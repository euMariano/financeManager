"""Funções utilitárias de autenticação e segurança."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.database import get_session
from app.models import User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("FINANCE_ACCESS_TOKEN_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("FINANCE_REFRESH_TOKEN_MINUTES", str(60 * 24 * 7))
)
SECRET_KEY = os.getenv("FINANCE_APP_SECRET", "change-me-in-production")

ACCESS_COOKIE = "finance_access_token"
REFRESH_COOKIE = "finance_refresh_token"
COOKIE_SECURE = os.getenv("FINANCE_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("FINANCE_COOKIE_SAMESITE", "lax")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str, token_type: str, expires_delta: Optional[timedelta] = None
) -> str:
    if SECRET_KEY == "change-me-in-production":
        # Segurança: evitar usar segredo padrão em produção.
        os.environ.setdefault("FINANCE_APP_SECRET_WARNING", "true")

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    return _create_token(
        subject,
        "access",
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    return _create_token(
        subject,
        "refresh",
        expires_delta or timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
    )


def _decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        ) from exc

    if payload.get("type") != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de token inválido"
        )
    return payload


def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_kwargs = {
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "path": "/",
    }
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )


def clear_auth_cookies(response: Response) -> None:
    cookie_kwargs = {
        "httponly": True,
        "secure": COOKIE_SECURE,
        "samesite": COOKIE_SAMESITE,
        "path": "/",
    }
    response.delete_cookie(ACCESS_COOKIE, **cookie_kwargs)
    response.delete_cookie(REFRESH_COOKIE, **cookie_kwargs)


def get_current_user(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> User:
    access_token = request.cookies.get(ACCESS_COOKIE)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária"
        )

    try:
        payload = _decode_token(access_token, expected_type="access")
    except HTTPException:
        # Tentativa de renovar via refresh token
        refresh_token = request.cookies.get(REFRESH_COOKIE)
        if not refresh_token:
            raise
        payload = _decode_token(refresh_token, expected_type="refresh")
        new_access = create_access_token(payload["sub"])
        set_auth_cookies(response, new_access, refresh_token)
        access_payload = _decode_token(new_access, expected_type="access")
        payload = access_payload

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
        )
    return user
