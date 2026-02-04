"""Lógica de negócio: porcentagem e faixa (vermelho/amarelo/verde)."""
from app.models import Card, Zone


def compute_percentage(value: float, net_balance: float) -> float:
    """Calcula a porcentagem do valor em relação ao saldo líquido."""
    if net_balance <= 0:
        return 0.0
    return round((value / net_balance) * 100, 2)


def compute_zone(net_balance: float, total_expenses: float, total_percentage: float) -> Zone:
    """
    Determina a faixa do usuário:
    - Vermelho: total das despesas > saldo líquido
    - Amarelo: despesas <= saldo mas total_percentage > 60
    - Verde: despesas <= saldo e total_percentage <= 60
    """
    if total_expenses > net_balance:
        return Zone.VERMELHO
    if total_percentage > 60:
        return Zone.AMARELO
    return Zone.VERDE


def get_totals_and_zone(cards: list[Card], net_balance: float) -> tuple[float, float, Zone]:
    """Retorna (total_expenses, total_percentage, zone)."""
    total_expenses = sum(c.value for c in cards)
    total_percentage = sum(c.percentage or 0 for c in cards)
    zone = compute_zone(net_balance, total_expenses, total_percentage)
    return total_expenses, total_percentage, zone
