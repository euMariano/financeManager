"""Endpoints de saldo líquido."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Balance, BalanceUpdate, User
from app.security import get_current_user

router = APIRouter(prefix="/balance", tags=["balance"])


def get_or_create_balance(session: Session, user: User) -> Balance:
    """Retorna o saldo do usuário ou cria registro inicial."""
    balance = session.exec(select(Balance).where(Balance.user_id == user.id).limit(1)).first()
    if balance is None:
        balance = Balance(user_id=user.id, net_balance=0.0)
        session.add(balance)
        session.commit()
        session.refresh(balance)
    return balance


@router.get("", response_model=Balance)
def get_balance(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Retorna o saldo líquido atual do usuário autenticado."""
    return get_or_create_balance(session, current_user)


@router.put("", response_model=Balance)
def update_balance(
    data: BalanceUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Define ou atualiza o valor do saldo líquido."""
    balance = get_or_create_balance(session, current_user)
    balance.net_balance = data.net_balance
    session.add(balance)
    session.commit()
    session.refresh(balance)
    return balance
