"""Mês corrente: do acumulado até hoje ao mês inteiro."""


def project(value_to_date: float, day: int, days_in_month: int) -> float:
    """Extrapola linearmente o acumulado até o fim do mês."""
    return value_to_date * days_in_month / day
