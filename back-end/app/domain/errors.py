"""Erros de negócio. A camada HTTP (controllers/errors.py) traduz cada um em status."""


class InvalidArea(ValueError):
    """Área mal formada ou fora do globo."""


class YearsOutOfRange(ValueError):
    """Período pedido fora do arquivo publicado."""


class RealtimeUnavailable(Exception):
    """Tempo real indisponível: sem chave, ou a fonte caiu sem snapshot em cache."""


class NotFound(LookupError):
    """Área ou célula inexistente na release."""


class ModelUnavailable(Exception):
    """Release sem previsão/território (contrato 1.0)."""


class AssistantUnavailable(Exception):
    """Sem ANTHROPIC_API_KEY no servidor, ou a API caiu."""
