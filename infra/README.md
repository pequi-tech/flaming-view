# infra · pipeline de dados do Calendário do Fogo

Transforma os focos de calor do NASA FIRMS (MODIS 2003→, VIIRS S-NPP 2012→, NOAA-20 2018→) numa
série única e comparável, **para o mundo inteiro**, por célula de 0,05° × mês, desde 2003.

```
pip install -r requirements.txt
make                          # mundo inteiro, 2003-2025 (~10 GB de download, ~1 h, pico de disco ~1 GB)
make COUNTRY=Brazil,Chile     # só alguns países (nomes como no FIRMS: United_States, Russian_Federation)
make test                     # unitários (sintéticos) + integração (metas de acurácia sobre os dados reais)
```

No macOS, se o Python não achar os certificados: `export SSL_CERT_FILE=/etc/ssl/cert.pem`.

## Etapas

| Script | Entrada → saída | O que faz |
|---|---|---|
| `fetch.py` | zips anuais do FIRMS → `data/agg/{sensor}_{ano}.csv.gz` | Baixa o zip mundial do ano, agrega país por país e apaga o zip. Nenhum CSV bruto fica em disco. Com `--country`, lê só os países pedidos via HTTP Range. Retomável. |
| `aggregate.py` | (biblioteca) | `clean()`: `type = 0`, confiança ≥ nominal (MODIS ≥ 30; VIIRS n/h). `cell_days()`: `raw` (detecções) e `cd01` (células-dia de 0,01° ≈ 1 km) por célula 0,05° × mês × sensor × dia/noite. O back-end usa as mesmas funções no tempo real. |
| `harmonize.py` | `data/agg/` → `data/grid/{ano}.parquet`, `factors.csv`, `metrics.json` | Calibra fatores, valida fora da amostra e monta a série `viirs_eq` ano a ano (memória baixa). |

## Regras fixas

- **Unidade:** células-dia de ~1 km. É a métrica em que o fator VIIRS/Aqua fica estável.
- **Elo AQUA←SNPP:** calibrado em **2013–2019**, validado em **2020–2021**. Aqua depois de 2021 nunca entra na calibração (deriva orbital).
- **Elo N20←SNPP:** calibrado em 2019–2025. **N21 ≈ N20** até existir arquivo anual do N21.
- **Fator hierárquico × mês:** célula 2° → bloco 10° → faixa de latitude 10° → global. Cada nível só vale com ≥ 100 células-dia VIIRS na calibração. Nunca um fator global direto: hemisférios têm estações opostas. A coluna `level` diz qual nível foi usado.
- **Fonte por ano:** AQUA 2003–2011 · SNPP 2012–2025 · N20 2026+. Uma fonte por ano, nunca soma de sensores.
- **Moeda:** `viirs_eq` = células-dia como o VIIRS S-NPP veria. "Focos equivalentes ao Aqua" = `viirs_eq × factor`.
- **Incerteza:** `lo`/`hi` só nos anos convertidos do Aqua (p10–p90 da razão previsto/real no hold-out). Nos anos VIIRS, `lo = hi = viirs_eq`.

## Saídas

`data/grid/{ano}.parquet` (o que o back-end carrega; um arquivo por ano, lido com filtro de bbox)

| coluna | significado |
|---|---|
| `lat05`, `lon05` | canto SW da célula de 0,05° |
| `year`, `month` | |
| `source` | AQUA / SNPP / N20 |
| `raw`, `cd01` | detecções e células-dia observadas no sensor de origem |
| `factor`, `level` | fator aplicado e nível da hierarquia (`c2`, `c10`, `band`, `global`, `observed`) |
| `viirs_eq` | **valor harmonizado** |
| `lo`, `hi` | faixa p10–p90 |

`data/factors.csv`: `link, level, lat, lon, month, factor`. `data/metrics.json`: MAPE, R², MdAPE do hold-out, participação de cada nível, quantis da incerteza.

## Testes (`test/`)

- `test_unit.py` — dados sintéticos; cada teste cai se uma regra for violada: filtros, células-dia (inclusive bordas exatas como 0,35°), qualquer lat/lon do globo, hierarquia de fallback (c2 → c10 → faixa → global), célula nunca vista, hold-out perfeito, série por fonte e incerteza.
- `test_integration.py` — roda só se `data/grid/` existir. Metas: **MAPE ≤ 10 %**, **R² ≥ 0,90**, ≥ 70 % das células com fator próprio, fator AQUA/SNPP mediano entre 0,15 e 0,35, N20/SNPP entre 0,9 e 1,1, sem degrau na troca de sensor (±50 %). Fatos conhecidos em três continentes: Pantanal jun/2024, Austrália dez/2019 (Black Summer), Quebec jun/2023 (pulam se a região não estiver nos dados). Integridade ano a ano.

## Fora de escopo (por enquanto)

- Fatores separados dia/noite: só se o app oferecer filtro dia/noite (o fator noturno é ~3× maior).
- Tempo real (API FIRMS NRT): fica no back-end, reutilizando `aggregate.clean` e `cell_days`.
- Níveis de detalhe para o globo (tiles 0,5°/2°): o back-end agrega o Parquet por bbox e zoom.
