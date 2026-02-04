"""Modelos de dados do organizador financeiro."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ExpenseType(str, Enum):
    """Tipos de despesa suportados."""
    CASA = "casa"
    FACULDADE = "faculdade"
    SAUDE = "saude"
    LAZER = "lazer"
    ALIMENTACAO = "alimentacao"
    TRANSPORTE = "transporte"
    OUTROS = "outros"


class CardStatus(str, Enum):
    """Status do card (despesa)."""
    PAGO = "pago"
    PENDENTE = "pendente"


class User(SQLModel, table=True):
    """Usuário autenticado do sistema."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50, description="Nome de usuário único")
    hashed_password: str = Field(description="Senha armazenada com hash")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação do usuário")


class UserCreate(SQLModel):
    """Payload para cadastro de usuário."""
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class UserRead(SQLModel):
    """Dados públicos do usuário."""
    id: int
    username: str
    created_at: datetime


class Balance(SQLModel, table=True):
    """Saldo líquido total do usuário (único registro por usuário)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True, description="Referência ao usuário dono do saldo")
    net_balance: float = Field(description="Valor do saldo líquido total")


class BalanceUpdate(SQLModel):
    """Schema para atualização do saldo."""
    net_balance: float


# --- Cards (despesas) ---

class CardBase(SQLModel):
    """Campos base de um card de despesa."""
    title: str = Field(default="", max_length=200, description="Título/nome da despesa (ex.: Aluguel, Mensalidade)")
    urgency: int = Field(ge=1, description="Grau de urgência (1 = maior prioridade)")
    expense_type: ExpenseType
    value: float = Field(gt=0, description="Valor da despesa")
    due_date: date = Field(description="Data para pagar")
    status: CardStatus = CardStatus.PENDENTE


class Card(CardBase, table=True):
    """Card de despesa persistido no banco."""
    id: Optional[int] = Field(default=None, primary_key=True)
    percentage: Optional[float] = Field(default=None, description="% em relação ao saldo líquido")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True, description="Usuário dono da despesa")


class CardCreate(CardBase):
    """Schema para criação de card (percentage é calculado pela API)."""
    pass


class CardUpdate(SQLModel):
    """Schema para atualização parcial de card."""
    title: Optional[str] = Field(default=None, max_length=200)
    urgency: Optional[int] = Field(default=None, ge=1)
    expense_type: Optional[ExpenseType] = None
    value: Optional[float] = Field(default=None, gt=0)
    due_date: Optional[date] = None
    status: Optional[CardStatus] = None


class CardRead(CardBase):
    """Schema de leitura de card (inclui id e percentage)."""
    id: int
    percentage: Optional[float] = None


# --- Resumo e faixa ---

class Zone(str, Enum):
    """Faixa de situação financeira."""
    VERMELHO = "vermelho"   # despesas > saldo
    AMARELO = "amarelo"     # despesas <= saldo mas > 60%
    VERDE = "verde"         # despesas <= saldo e <= 60%


class Summary(SQLModel):
    """Resumo financeiro com faixa e totais."""
    net_balance: float
    total_expenses: float
    total_percentage: float
    zone: Zone
    cards_count: int
