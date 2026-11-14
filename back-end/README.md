# back-end · API do Calendário do Fogo (MVP)

Serve a release validada do `serving/` (atividade de fogo harmonizada MODIS×VIIRS, 2003–2025, mundo inteiro)
e o mês corrente em tempo real (FIRMS NRT). FastAPI + DuckDB direto nos Parquet + cache SQLite.

```
pip install -r requirements.txt
make run              # http://localhost:8000  ·  docs interativas em /docs
make test             # 36 testes: domínio, API (release sintética + FIRMS falso), release real
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

## Arquitetura (DDD, uma camada por arquivo)

```
app/domain.py    regras puras: BBox (validação, antimeridiano, células que tocam a caixa), climatologia
                 (ano sem linha = 0), nível, projeção do mês corrente
app/service.py   casos de uso: calendar, series, cells, current, method
app/infra.py     Release: DuckDB sobre os Parquet do manifest; recusa subir se arquivo/contrato não batem
                 Firms: API de área NRT em janelas de 5 dias, mesmos filtros do pipeline (infra/aggregate.py)
                 Cache: SQLite chave-valor; serve o último snapshot (stale=true) se o FIRMS cair
app/api.py       FastAPI: validação (422), 503 sem tempo real, gzip, CORS, Cache-Control
```

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
