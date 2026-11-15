"""Assistente ancorado (RF-API-07/08): monta o contexto com as mesmas saídas da API e pede ao LLM que explique.
O LLM redige; não decide. Sem chave, o front usa os textos das regras."""
import json

from ..domain.errors import AssistantUnavailable
from ..domain.territory import Area
from ..infra.llm import Llm
from .forecast_service import ForecastService
from .territory_service import TerritoryService

MAX_CONTEXT_CHARS = 48_000            # ≈ 12 k tokens (RNF-04)
LANG = {'pt-BR': 'português do Brasil', 'en': 'English'}
SYSTEM = """Você é o assistente do Flaming View, plataforma de apoio à decisão preventiva contra incêndios para a Defesa Civil.
Responda sempre em {lang}. Use apenas números presentes no CONTEXTO (JSON abaixo, saído da API); cite a origem entre
colchetes, ex.: [/cell], [/forecast], [/priorities]. Se a pergunta pedir algo que não está no contexto, diga que não tem esse dado.
O IPP (N^0,5·V^0,25·E^0,25) ordena atenção; nunca o apresente como probabilidade. A classe prevista compara a atividade
esperada com a própria série da célula; não é probabilidade de incêndio individual. Recomendações apoiam o gestor, que decide.
Seja breve e objetivo (até ~180 palavras), sem títulos markdown.

CONTEXTO:
{context}"""
REPORT = """Redija o resumo de um plano preventivo mensal para a área do contexto, com as seções: Resumo executivo,
Prioridades, Ações deliberadas (aceitas e ignoradas, com motivos), Ressalvas. Texto corrido curto em cada seção."""


class AssistantService:
    def __init__(self, llm: Llm, forecast: ForecastService, territory: TerritoryService):
        self.llm, self.forecast, self.territory = llm, forecast, territory

    def context(self, area: Area | None, cell_id: int | None, horizon: int, extra: dict | None = None) -> str:
        ctx = {}
        if area:
            ctx['/forecast'] = self.forecast.forecast(area)
            p = self.territory.priorities(area, horizon, 10)
            ctx['/priorities'] = {**p, 'items': [{k: v for k, v in i.items() if k not in ('lat', 'lon')} for i in p['items']]}
        if cell_id is not None:
            c = self.territory.cell(cell_id)
            ctx['/cell'] = {**c, 'climatology': None}
        if extra:
            ctx['plan'] = extra
        text = json.dumps(ctx, ensure_ascii=False, separators=(',', ':'), default=str)
        return text[:MAX_CONTEXT_CHARS]    # ponytail: corte bruto; ordem acima põe o essencial primeiro

    def ask(self, messages: list[dict], area: Area | None, cell_id: int | None, horizon: int, lang: str):
        if not self.llm.available:
            raise AssistantUnavailable('no_key')
        system = SYSTEM.format(lang=LANG.get(lang, LANG['en']), context=self.context(area, cell_id, horizon))
        return self.llm.stream(system, messages)

    def report(self, area: Area, horizon: int, lang: str, plan: dict):
        if not self.llm.available:
            raise AssistantUnavailable('no_key')
        system = SYSTEM.format(lang=LANG.get(lang, LANG['en']), context=self.context(area, None, horizon, plan))
        return self.llm.stream(system, [{'role': 'user', 'content': REPORT}])
