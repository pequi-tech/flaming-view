# serving · dados padronizados para o back-end

Camada entre o pipeline (`../infra`) e o back-end. Pega a saída do infra, padroniza no formato do
**`contract.json`**, valida tudo e publica uma *release* versionada e imutável. O back-end só lê
`release/CURRENT`; nunca lê `infra/data` direto.

```
make publish     # infra/data -> release/{versão}/ ; troca release/CURRENT só se tudo passar (~20 s)
make verify      # confere checksums + versão do contrato da release atual
make test        # 21 unitários (cada regra recusa dado ruim) + 5 de integração (release real)
```

## O que o back-end recebe

```
release/
├─ CURRENT                       versão ativa, ex.: 20261114T180340Z
└─ 20261114T180340Z/
   ├─ grid/year=2003.parquet ... year=2025.parquet
   ├─ factors.parquet
   ├─ metrics.json               validação hold-out do infra
   └─ manifest.json              versão do contrato, linhas, relatório de qualidade, sha256 de cada arquivo
```

Leitura recomendada (bbox + mês usam as estatísticas dos row groups, não leem o arquivo todo):
```python
pd.read_parquet(f'release/{v}/grid/year=2024.parquet', columns=['cell_id', 'month', 'activity'],
                filters=[('lat', '>=', -22), ('lat', '<=', -16), ('lon', '>=', -58), ('lon', '<=', -54)])
# DuckDB: SELECT ... FROM read_parquet('release/{v}/grid/*.parquet', hive_partitioning = true)
```

### `grid` — uma linha por célula 0,05° × ano × mês com fogo (sem linha = zero)

| coluna | tipo | regra |
|---|---|---|
| `cell_id` | int32 | `(round(lat*20)+1800)*7200 + (round(lon*20)+3600)`. Chave para joins; nunca use float como chave |
| `lat`, `lon` | float64 | canto SW, múltiplo de 0,05; lat ∈ [−60, 89,95], lon ∈ [−180, 179,95] |
| `year` | int16 | igual ao da partição |
| `month` | int8 | 1–12 |
| `source` | category | AQUA (2003–11), SNPP (2012–25), N20 (2026+) |
| `detections` | int32 | ≥ 1 |
| `cell_days` | int32 | ≥ 1 e ≤ `detections` |
| `factor` | float32 | > 0; = 1 quando SNPP |
| `factor_level` | category | `observed` ⇔ SNPP; senão `c2`/`c10`/`band`/`global` |
| `activity` | float32 | **valor harmonizado** = `cell_days / factor` |
| `activity_lo`, `activity_hi` | float32 | `lo ≤ activity ≤ hi`; iguais a `activity` quando observado |

Unicidade `(cell_id, year, month)`; ordenado por `(cell_id, month)` dentro de cada ano.

### `factors`

`link` (AQUA_SNPP, N20_SNPP), `level` (c2, c10, band, global), `lat`/`lon` (nulos onde o nível não usa), `month`, `factor > 0`.

## Garantias de qualidade (a release é recusada se qualquer uma falhar)

1. **Contrato:** colunas exatas, tipos, nulos, enums, mínimos e máximos, unicidade e ordem.
2. **Entre colunas:** grade de 0,05° e `cell_id` coerentes; ano e fonte batem com a partição; `cell_days ≤ detections`; `activity = cell_days / factor`; faixa de incerteza coerente; SNPP nunca convertido.
3. **Completude:** todo ano fechado tem os 12 meses.
4. **Série:** atividade global não pode variar mais de 3× entre anos seguidos (pega troca de sensor mal harmonizada).
5. **Validação do infra:** MAPE ≤ 10 %, R² ≥ 0,90, ≥ 70 % das células com fator próprio.
6. **Limpeza documentada:** Antártida (lat < −60) é descartada, porque lá não há vegetação. Foram 641 linhas de 47,6 M, todas do S-NPP. Focos acima de 75° N são mantidos (pode ser tundra) e contados no `manifest.json`.
7. **Publicação atômica:** escreve numa pasta temporária, renomeia, e só então troca `CURRENT`. Se a release é recusada, a atual continua e nenhum lixo fica para trás.
8. **Integridade:** `manifest.json` traz o sha256 de cada arquivo. `make verify` (ou `publish.verify()` no boot do back-end) detecta arquivo corrompido ou contrato com major incompatível.

## Para o validador do back-end

Reutilize o `contract.json`: dtype, `nullable`, `enum`, `min`/`max`/`exclusive_min` e `unique` de cada coluna estão lá. `publish.check_columns(df, spec)` já implementa essas regras genéricas. A versão do contrato segue semver: mudança de major quebra o back-end, e o `verify` acusa.
