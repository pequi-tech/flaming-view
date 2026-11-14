"""Erros de negócio. A camada HTTP (controllers/errors.py) traduz cada um em status."""


class InvalidArea(ValueError):
    """Área mal formada ou fora do globo."""


class YearsOutOfRange(ValueError):
    """Período pedido fora do arquivo publicado."""


class RealtimeUnavailable(Exception):
    """Tempo real indisponível: sem chave, ou a fonte caiu sem snapshot em cache."""
