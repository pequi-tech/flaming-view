# back-end · API do Calendário do Fogo (MVP)

Serve a release validada do `serving/` (atividade de fogo harmonizada MODIS×VIIRS, 2003–2025, mundo inteiro)
e o mês corrente em tempo real (FIRMS NRT). FastAPI + DuckDB direto nos Parquet + cache SQLite.

```
pip install -r requirements.txt
make run              # http://localhost:8000  ·  docs interativas em /docs
make test             # 42 testes: domínio, API (release sintética + FIRMS falso), release real, arquitetura
```

| Variável | Padrão | Para quê |
|---|---|---|
| `FV_RELEASE` | `../serving/release` | pasta com `CURRENT` (gerada por `make publish` no serving) |
| `FIRMS_MAP_KEY` | — | chave do FIRMS para `/current`. Sem ela, `/current` responde 503 e o resto funciona |
| `FV_CACHE` | `cache.db` | arquivo SQLite do cache do tempo real |
| `FV_CORS` | `*` | origens permitidas, separadas por vírgula |
| `FV_VERIFY_SHA` | — | `1` = confere o sha256 de todos os arquivos no boot (~1 s a mais) |

## Endpoints

Área sempre como `bbox=oeste,sul,leste,norte` em graus. Oeste > leste = cruza o antimeridiano
(ex.: `160,55,-170,72`). Unidade de todos os valores: **células-dia equivalentes VIIRS S-NPP**, comparável de 2003 a hoje.

| Rota | Parâmetros | Devolve |
|---|---|---|
| `GET /health` | — | `status`, `release`, `years`, `realtime` (se há MAP_KEY) |
| `GET /calendar` | `bbox`, `from_year?`, `to_year?`, `format=json\|csv` | matriz ano × mês completa (meses sem fogo = 0). Cada mês traz `value`, `lo`, `hi`, `source`, `estimated`, `median`, `p75`, `p90`, `ratio` e `level` (`baixo`, `normal`, `alto`, `critico`). A climatologia usa sempre todo o arquivo, mesmo com recorte de anos. CSV = download para relatório |
| `GET /series` | `bbox`, `from_year?`, `to_year?` | total por ano com `lo`/`hi` e sensor |
| `GET /cells` | `year`, `month`, `res` ∈ {0.25, 0.5, 1, 2}, `bbox?` | camada do globo: `[{lat, lon, value}]`, canto SW da célula de `res` graus |
| `GET /current` | `bbox` | mês corrente: `value_to_date`, `projected` (extrapolado para o mês todo), `median`/`p75`/`p90`, `ratio`, `level`, `stale` |
| `GET /method` | — | métricas da validação (MAPE, R²), versão do contrato e qualidade da release |

Nível do mês: `critico` ≥ p90 do mesmo mês na área; `alto` ≥ p75; `baixo` < p25; senão `normal`.
Área sem histórico de fogo nunca vira alerta.

Exemplo: `GET /calendar?bbox=-58,-22,-54,-16&from_year=2024&to_year=2024`, junho:
`{"value": 9510, "median": 837, "ratio": 11.36, "level": "critico", "source": "SNPP", "estimated": false, ...}`

## Arquitetura (DDD, atomizada)

```
app/
├─ main.py                 raiz de composição: infra -> services -> controllers -> routes
├─ config.py               configuração do ambiente (lida ao criar o app)
├─ domain/                 regras puras, sem IO nem framework
│  ├─ area.py              BBox: validação, antimeridiano, células que tocam a caixa
│  ├─ years.py             período dentro do arquivo
│  ├─ climatology.py       p25/mediana/p75/p90 do mês (ano sem linha = 0) e nível
│  ├─ calendar.py          matriz ano × mês e totais anuais
│  ├─ projection.py        mês corrente -> mês inteiro
│  ├─ units.py             unidade dos valores
│  └─ errors.py            InvalidArea, YearsOutOfRange, RealtimeUnavailable
├─ infra/                  mundo externo
│  ├─ release.py           DuckDB sobre os Parquet; recusa subir se arquivo/contrato não batem
│  ├─ firms.py             FIRMS NRT: janelas de 5 dias em paralelo, filtros do infra/aggregate.py
│  └─ cache.py             SQLite chave-valor; último snapshot se a fonte cair
├─ services/               casos de uso (um por arquivo)
│  ├─ calendar_service.py  calendário e série
│  ├─ map_service.py       células do globo
│  ├─ realtime_service.py  mês corrente
│  └─ system_service.py    saúde e método
├─ controllers/            HTTP <-> domínio: converte entrada, escolhe JSON/CSV, cache HTTP
│  ├─ *_controller.py
│  ├─ input_dto.py         schemas Pydantic para query params
│  ├─ output_dto.py        schemas Pydantic para cada resposta e erro
│  ├─ responses.py         valida DTOs, política de Cache-Control e CSV
│  └─ errors.py            intercepta erros e serializa ErrorResponseDTO
└─ routes/                 só declara rotas e parâmetros (OpenAPI) e delega ao controller
   ├─ *_routes.py
   └─ DTOs de query + response_model para cada rota
tests/
├─ domain/                 uma suíte por módulo de domínio
├─ api/                    uma suíte por grupo de rotas (release sintética + FIRMS falso)
├─ integration/            release real: eventos conhecidos e metas de latência
├─ fixtures.py             release mínima com o contrato real, FIRMS falso, caso base
└─ test_architecture.py    fronteiras entre camadas e tamanho dos arquivos
```

Todas as rotas JSON declaram `response_model` e validam o DTO antes de serializar. Erros de validação,
domínio, HTTP e exceções inesperadas usam o mesmo formato `{"error":{"code","message","details?"}}`.
Os parâmetros de query também são DTOs Pydantic com campos extras recusados e aparecem no OpenAPI.

Regras de dependência, verificadas pelo `test_architecture.py`:

| Camada | Não pode importar |
|---|---|
| domain | infra, services, controllers, routes, fastapi, duckdb, pandas, sqlite3, urllib |
| infra | services, controllers, routes, fastapi |
| services | controllers, routes, fastapi |
| controllers | infra, routes |
| routes | services, infra, domain |

## Desempenho (release real, 47,6 M linhas, máquina de dev)

| Requisição | Tempo | Payload gzip |
|---|---|---|
| `/calendar` Pantanal | ~50 ms | 6 KB |
| `/calendar` mundo inteiro | ~230 ms | 7 KB |
| `/cells` mundo, 1° | ~60 ms | 32 KB |
| `/cells` mundo, 0,25° | ~240 ms | 171 KB |

O arquivo histórico não usa cache no servidor: o DuckDB lê só os row groups da caixa, e a release é imutável.
As respostas saem com `Cache-Control: max-age=86400` (`/current`: 300 s), então navegador e CDN seguram.

O SQLite só cacheia o FIRMS, que é lento, tem limite de requisições e cai. O mês corrente é buscado em janelas
de 5 dias, em paralelo. As janelas dos últimos 2 dias valem 1 h no cache; as anteriores valem 7 dias, porque
já não mudam no NRT.

`/current` medido com o FIRMS real (14/11/2026):

| Área | 1ª chamada | com cache |
|---|---|---|
| Pantanal | ~1 s | ~25 ms |
| Brasil | ~3 s | ~170 ms |
| Chukotka (cruza o antimeridiano) | ~1 s | ~20 ms |
| Austrália SE | 3–6 s (variação do FIRMS) | ~35 ms |

Rodar com tempo real: `FIRMS_MAP_KEY=<sua chave> make run`. A chave fica só no ambiente: não vai para
código, git, logs nem para a chave do cache.

## Fora do MVP (de propósito)

- Polígono exato de país: a área é a bbox que o front já calcula. Países com fronteira irregular incluem vizinhos na borda.
- Autenticação e rate limit: API só de leitura, sem dado sensível.
- Calibração NOAA-21: tratado como S-NPP (o elo NOAA-20/S-NPP medido é 1,01). O FIRMS já tem `VIIRS_NOAA21_SP` de 03/2023 a 07/2026, então dá para calibrar quando precisar.
- Fontes estáticas no tempo real: o NRT do FIRMS não traz `type`, então chamas de gás e indústria entram no `/current`.

## Contrato 1.1 · previsão, prioridade e assistente

A release passa a trazer `predictions.parquet`, `territory.parquet`, `areas.parquet`, `model_metrics.json` e `areas/*.geojson`
(gerados por `make -C infra model` e publicados por `make -C serving publish`). No boot, `infra/model_store.py` junta previsão
e território numa tabela em memória e calcula o IPP com os pesos de `domain/ipp_params.py` (não materializado).
Release 1.0 continua subindo: as rotas novas respondem `503 model_unavailable`.

| Rota | O que devolve |
|---|---|
| `GET /forecast?area_id=BR5218805[&horizon=1]` | classes previstas por horizonte, total com faixa, mediana do mês, ano anterior, métricas do modelo, breadcrumb |
| `GET /cells?layer=forecast\|ipp\|history&horizon=1&shape=h3&h3_res=5&area_id=…` | camada do mapa em hexágonos H3 (ou `shape=square` com `bbox`) |
| `GET /cell/{cell_id}` | lugar (município, UF, TI), previsão M+1..M+3, IPP com N/V/E e explicação, 24 meses, fatores, recomendações |
| `GET /priorities?area_id=…&horizon=1&limit=20` | país/UF → municípios; município → células; fora do Brasil → hexágonos res 5 |
| `GET /areas?q=rio ver` · `GET /areas/{id}/geometry` | busca sem acento e GeoJSON simplificado |
| `POST /assistant` · `POST /assistant/report` | SSE (`data: {"text"}` … `data: [DONE]`); sem `ANTHROPIC_API_KEY` → `503 assistant_unavailable` |

Regras R1–R8 em `domain/recommendations.py` (puras, um teste por regra). O LLM (`claude-opus-5`, `infra/llm.py`) só redige;
o contexto enviado é a saída das próprias rotas, cortada em ~12 k tokens.
