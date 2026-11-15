"""Cliente da API da Anthropic (só no servidor). A chave vem do ambiente e nunca é registrada nem devolvida."""
import anthropic

from ..domain.errors import AssistantUnavailable

MODEL = 'claude-opus-5'


class Llm:
    def __init__(self, api_key: str | None, timeout: float = 60.0):
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=1) if api_key else None

    @property
    def available(self) -> bool:
        return self.client is not None

    def stream(self, system: str, messages: list[dict]):
        """Gera os pedaços de texto da resposta. Erros viram AssistantUnavailable sem a mensagem original (pode ecoar cabeçalhos)."""
        if not self.client:
            raise AssistantUnavailable('no_key')
        try:
            with self.client.beta.messages.stream(
                model=MODEL, max_tokens=4096, system=system, messages=messages,
                thinking={'type': 'adaptive'}, output_config={'effort': 'medium'},
                betas=['server-side-fallback-2026-07-01'], extra_body={'fallbacks': 'default'},
            ) as s:
                yield from s.text_stream
                if s.get_final_message().stop_reason == 'refusal':
                    yield '\n\n[resposta recusada pelo modelo]'
        except anthropic.APIStatusError as e:   # motivo vira um código fixo; a mensagem do provedor não sai daqui
            billing = e.status_code in (400, 402) and 'credit' in str(getattr(e, 'message', '')).lower()
            raise AssistantUnavailable('billing' if billing else 'auth' if e.status_code in (401, 403) else 'upstream') from None
        except anthropic.APIError:
            raise AssistantUnavailable('upstream') from None
