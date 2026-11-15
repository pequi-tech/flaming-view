"""DTOs do assistente (entrada; a saída é SSE)."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'assistant']
    content: str = Field(..., min_length=1, max_length=4000)


class AssistantRequestDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    messages: list[ChatMessageDTO] = Field(..., min_length=1, max_length=20)
    area_id: str | None = None
    cell_id: int | None = None
    horizon: Literal[1, 2, 3] = 1
    lang: Literal['pt-BR', 'en'] = 'pt-BR'


class ReportRequestDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')
    area_id: str
    horizon: Literal[1, 2, 3] = 1
    lang: Literal['pt-BR', 'en'] = 'pt-BR'
    accepted: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    ignored: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
