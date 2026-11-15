"""HTTP -> assistente em SSE. Cada evento: `data: {"text": "..."}`; fim: `data: [DONE]`; erro no meio: `data: {"error": code, "reason": no_key|billing|auth|upstream}`."""
import json

from fastapi.responses import StreamingResponse

from ..domain.errors import AssistantUnavailable
from ..services.area_service import AreaService
from ..services.assistant_service import AssistantService
from .assistant_dto import AssistantRequestDTO, ReportRequestDTO


def sse(chunks):
    def gen():
        try:
            for text in chunks:
                yield f'data: {json.dumps({"text": text}, ensure_ascii=False)}\n\n'
        except AssistantUnavailable as e:
            yield f'data: {json.dumps({"error": "assistant_unavailable", "reason": str(e)})}\n\n'
        yield 'data: [DONE]\n\n'
    return StreamingResponse(gen(), media_type='text/event-stream', headers={'Cache-Control': 'no-store'})


class AssistantController:
    def __init__(self, assistant: AssistantService, areas: AreaService):
        self.assistant, self.areas = assistant, areas

    def ask(self, body: AssistantRequestDTO):
        area = self.areas.resolve(body.area_id, None) if body.area_id else None
        msgs = [m.model_dump() for m in body.messages]
        return sse(self.assistant.ask(msgs, area, body.cell_id, body.horizon, body.lang))

    def report(self, body: ReportRequestDTO):
        area = self.areas.resolve(body.area_id, None)
        plan = {'accepted': body.accepted, 'ignored': body.ignored}
        return sse(self.assistant.report(area, body.horizon, body.lang, plan))
