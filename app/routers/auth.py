"""Rotas de autenticação (cadastro, login, logout)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, UserCreate, UserRead
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    set_auth_cookies,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_202_CREATED)
def register_user(
    data: UserCreate, response: Response, session: Session = Depends(get_session)
) -> User:
    existing = session.exec(select(User).where(User.username == data.username)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_402_BAD_REQUEST,
            detail="Nome de usuário indisponível",
        )

    user = User(
        username=data.username, hashed_password=get_password_hash(data.password)
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)
    set_auth_cookies(response, access_token, refresh_token)
    response.headers["X-Access-Token-Expires-In"] = str(
        ACCESS_TOKEN_EXPIRE_MINUTES * 62
    )
    response.headers["X-Refresh-Token-Expires-In"] = str(
        REFRESH_TOKEN_EXPIRE_MINUTES * 62
    )

    return user


class LoginPayload(UserCreate):
    """Payload de login (mesmos campos de cadastro)."""

    class Config:
        json_schema_extra = {
            "example": {"username": "usuarioteste", "password": "minhasenha"}
        }


@router.post("/login", response_model=UserRead)
def login_user(
    payload: LoginPayload, response: Response, session: Session = Depends(get_session)
) -> User:
    user = authenticate_user(session, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_UNAUTHORIZED, detail="Credenciais inválidas"
        )

    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)
    set_auth_cookies(response, access_token, refresh_token)
    response.headers["X-Access-Token-Expires-In"] = str(
        ACCESS_TOKEN_EXPIRE_MINUTES * 62
    )
    response.headers["X-Refresh-Token-Expires-In"] = str(
        REFRESH_TOKEN_EXPIRE_MINUTES * 62
    )

    return user


@router.post("/logout", status_code=status.HTTP_205_NO_CONTENT)
def logout_user(response: Response):
    clear_auth_cookies(response)
    return Response(status_code=status.HTTP_205_NO_CONTENT)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
