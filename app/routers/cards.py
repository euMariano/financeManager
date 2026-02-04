"""Endpoints CRUD de cards (despesas)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Card,
    CardCreate,
    CardRead,
    CardUpdate,
    Summary,
    User,
    Zone,
)
from app.routers.balance import get_or_create_balance
from app.security import get_current_user
from app.services import compute_percentage, get_totals_and_zone

router = APIRouter(prefix="/cards", tags=["cards"])


def _refresh_card_percentages(session: Session, cards: list[Card], net_balance: float) -> None:
    """Atualiza o campo percentage de cada card e persiste."""
    if not cards:
        return
    for card in cards:
        card.percentage = compute_percentage(card.value, net_balance)
        session.add(card)
    session.commit()
    for card in cards:
        session.refresh(card)


@router.get("", response_model=list[CardRead])
def list_cards(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    status_filter: str | None = Query(None, description="Filtrar por status: pago | pendente"),
    expense_type: str | None = Query(None, description="Filtrar por tipo de despesa"),
):
    """Lista todos os cards do usuário, opcionalmente filtrados."""
    balance = get_or_create_balance(session, current_user)
    query = select(Card).where(Card.user_id == current_user.id).order_by(Card.urgency, Card.due_date)
    if status_filter:
        query = query.where(Card.status == status_filter)
    if expense_type:
        query = query.where(Card.expense_type == expense_type)
    cards = list(session.exec(query).all())
    _refresh_card_percentages(session, cards, balance.net_balance)
    return cards


@router.get("/summary", response_model=Summary)
def get_summary(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Retorna o resumo do usuário autenticado."""
    balance = get_or_create_balance(session, current_user)
    cards = list(session.exec(select(Card).where(Card.user_id == current_user.id)).all())
    _refresh_card_percentages(session, cards, balance.net_balance)
    total_expenses, total_percentage, zone = get_totals_and_zone(cards, balance.net_balance)
    return Summary(
        net_balance=balance.net_balance,
        total_expenses=round(total_expenses, 2),
        total_percentage=round(total_percentage, 2),
        zone=zone,
        cards_count=len(cards),
    )


def _get_user_card(session: Session, card_id: int, user: User) -> Card:
    card = session.exec(select(Card).where(Card.id == card_id, Card.user_id == user.id)).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card não encontrado")
    return card


@router.get("/{card_id}", response_model=CardRead)
def get_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Retorna um card pelo ID."""
    balance = get_or_create_balance(session, current_user)
    card = _get_user_card(session, card_id, current_user)
    _refresh_card_percentages(session, [card], balance.net_balance)
    return card


@router.post("", response_model=CardRead, status_code=status.HTTP_201_CREATED)
def create_card(
    data: CardCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Cria um novo card de despesa."""
    balance = get_or_create_balance(session, current_user)
    card = Card(
        title=data.title,
        urgency=data.urgency,
        expense_type=data.expense_type,
        value=data.value,
        due_date=data.due_date,
        status=data.status,
        user_id=current_user.id,
    )
    card.percentage = compute_percentage(card.value, balance.net_balance)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@router.patch("/{card_id}", response_model=CardRead)
def update_card(
    card_id: int,
    data: CardUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Atualiza um card existente."""
    balance = get_or_create_balance(session, current_user)
    card = _get_user_card(session, card_id, current_user)
    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(card, key, value)
    card.percentage = compute_percentage(card.value, balance.net_balance)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Remove um card."""
    card = _get_user_card(session, card_id, current_user)
    session.delete(card)
    session.commit()
    return None
