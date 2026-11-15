# Flaming View

**Inteligência preditiva para prevenção de incêndios.** Plataforma de apoio à decisão para a Defesa Civil:
prevê onde o fogo tende a se concentrar nos próximos três meses, prioriza territórios pela exposição de pessoas
e terras indígenas e sugere ações preventivas que o gestor aceita ou ignora, com relatório em PDF.

> Protótipo do **NASA Space Apps Challenge 2026**, desafio #8 *Harmonization of MODIS and VIIRS Hot Spots*.
> Não é sistema oficial.

*Prever é o começo. Priorizar é o diferencial. Preparar-se antes é o impacto.*

## Uso de SI (Super Inteligence)

Partes do código, da documentação e do processamento de dados deste projeto foram geradas com auxílio do
**Claude (Anthropic)**, sempre revisadas e testadas pela equipe.

- **Fluxo:** Plan Mode com **Spec-Driven Development**. Primeiro a especificação (PRD), depois o desenho, as tarefas
  e a implementação, cada uma verificada contra a anterior.
- **PRD:** requisitos escritos no modelo **EARS** (*Easy Approach to Requirements Syntax*), com prioridade
  (P0–P5) e critério de aceite verificável para cada um.
- **Revisão:** agentes de SI simularam um especialista de UX/UI e um coordenador de Defesa Civil; os pareceres
  viraram o backlog de ajustes.
- **No produto:** o assistente usa o Claude (`claude-opus-5`) só para **redigir e explicar** números já
  calculados pela API. Ele não decide nem gera previsões; as recomendações vêm de regras fixas e auditáveis.

## Como funciona

1. **Histórico harmonizado (2003–2026).** Focos MODIS e VIIRS (NASA FIRMS) convertidos para uma série única em
   "células-dia equivalentes VIIRS" por célula de 0,05° × mês. Validação fora da amostra: MAPE 4,7 %, R² 0,96.
2. **Previsão M+1, M+2, M+3.** Random Forest por horizonte (células de 0,5°, desagregadas para 0,05°), com
   histórico de fogo, ONI (El Niño/La Niña) e anomalias NASA POWER (chuva, temperatura, umidade, vento).
   Treino até 2022, teste 2023–2025: AUC 0,71 / 0,66 / 0,65; nos 10 % mais alertados de M+1 acerta 34 % contra
   14 % de base (2,4× o acaso). M+2 e M+3 aparecem como tendência.
3. **Prioridade (IPP).** `IPP = N^0,5 · V^0,25 · E^0,25`, cada componente em [0,05; 1]:
   - **N, previsão:** rank(fogo previsto)^0,75 · rank(previsto ÷ mediana)^0,25, entre células com fogo previsto;
   - **V, histórico:** rank da atividade acumulada 2003–2025;
   - **E, exposição:** max(rank da população GHSL 2025 da célula ; 0,8 se ≥ 20 % em terra indígena).

   Classes por quantis entre células com fogo previsto; "Máxima" exige fogo acima do normal. O IPP ordena atenção;
   não é probabilidade de desastre.
4. **Ações.** Oito regras (R1–R8) ligadas às decisões D1–D5 (pré-posicionar, alertar, fiscalizar, pedir reforço,
   plano de contingência). O gestor aceita ou ignora cada ação; a decisão entra no relatório em PDF.

## Estrutura

| Pasta | O que é |
|---|---|
| `infra/` | Pipeline de dados: FIRMS → série harmonizada; modelo (`features.py`, `model.py`); território, áreas, GHSL e POWER (`territory.py`, `power.py`). |
| `serving/` | Valida contra `contract.json` e publica uma *release* versionada com checksums. |
| `back-end/` | API FastAPI + DuckDB (domain → infra → services → controllers → routes). |
| `front-end/` | React + Vite + MapLibre: Situação, Mapa, Territórios, Plano, Relatório, Assistente, Método (PT-BR/EN). |
| `video/` | Captura e montagem do vídeo de demonstração. |

## Rodar localmente

Requisitos: Python 3, Node.js e npm.

```bash
cp .env.example .env    # opcional: FIRMS_MAP_KEY (tempo real) e ANTHROPIC_API_KEY (assistente)
./start.sh              # API em http://localhost:8000 (docs em /docs) · interface em http://localhost:5180
```

O `start.sh` instala dependências na primeira vez, confere os checksums da release e sobe os dois serviços
(`Ctrl+C` encerra). Sem chaves, tudo funciona exceto o mês corrente em tempo real e o assistente.

Para gerar os dados do zero (downloads longos):

```bash
make -C infra && make -C infra model     # série harmonizada, previsão, território (GHSL, POWER, IBGE, TIs)
make -C serving publish                  # release em serving/release/
```

Testes: `make -C back-end test`, `make -C serving test`, `make -C infra test`, `cd front-end && npm run build`.

## Fontes de dados

| Fonte | O que usamos | Acesso |
|---|---|---|
| **NASA FIRMS** · MODIS Collection 6.1 (Aqua/Terra) | focos de calor 2003–2025 para a série harmonizada | [arquivos anuais por país](https://firms.modaps.eosdis.nasa.gov/download/) |
| **NASA FIRMS** · VIIRS 375 m S-NPP | referência da série (2012–2025) e calibração dos fatores | [FIRMS](https://firms.modaps.eosdis.nasa.gov/) |
| **NASA FIRMS** · VIIRS 375 m NOAA-20 (SP e NRT) | 2026 do Brasil (jan–out) | [API de área FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) |
| **NASA FIRMS** · VIIRS 375 m NOAA-21 (NRT) | mês corrente em tempo real | [API de área FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) |
| **NASA POWER** (mensal, MERRA-2/IMERG) | chuva (PRECTOTCORR), temperatura (T2M), umidade (RH2M), vento (WS2M), América do Sul 2003–2026 | [NASA POWER](https://power.larc.nasa.gov/) · [docs](https://power.larc.nasa.gov/docs/) |
| **NOAA CPC · ONI** (Oceanic Niño Index) | El Niño/La Niña como variável do modelo | [oni.ascii.txt](https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt) · [tabela ONI](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php) |
| **GHSL GHS-POP R2023A** (JRC/Comissão Europeia), época 2025, 30″ | população por célula para a exposição E | [GHS-POP R2023A](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php) · [download](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/) |
| **IBGE** · malhas territoriais 2024 (API v3) | estados e municípios, busca e recorte | [API de malhas](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3) |
| **IBGE** · população estimada 2024 (tabela 6579) | população municipal (conferência e versão sem GHSL) | [API de agregados](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3) |
| **IBGE** · localidades | nomes de municípios e UFs | [API de localidades](https://servicodados.ibge.gov.br/api/docs/localidades) |
| **FUNAI** · terras indígenas, via **TerraBrasilis/INPE (PRODES)** | exposição E_ti, regra R3 e nome da TI | [TerraBrasilis](https://terrabrasilis.dpi.inpe.br/) · [FUNAI geoprocessamento](https://www.gov.br/funai/pt-br/atuacao/terras-indigenas/geoprocessamento-e-mapas) |
| **Natural Earth** 1:50m | fronteiras de países e população fora do Brasil | [Natural Earth](https://www.naturalearthdata.com/) |
| **NASA GIBS** | fundo do mapa (Blue Marble) e camadas de satélite | [GIBS API docs](https://nasa-gibs.github.io/gibs-api-docs/) |
| **H3** (Uber) | grade hexagonal da camada visual | [h3geo.org](https://h3geo.org/) |

## Estudos e referências

- Giglio, L.; Schroeder, W.; Justice, C. O. (2016). *The collection 6 MODIS active fire detection algorithm and fire
  products.* Remote Sensing of Environment, 178, 31–41. [doi:10.1016/j.rse.2016.02.054](https://doi.org/10.1016/j.rse.2016.02.054). Base dos focos MODIS.
- Schroeder, W.; Oliva, P.; Giglio, L.; Csiszar, I. A. (2014). *The New VIIRS 375 m active fire detection data product:
  Algorithm description and initial assessment.* Remote Sensing of Environment, 143, 85–96. [doi:10.1016/j.rse.2013.12.008](https://doi.org/10.1016/j.rse.2013.12.008). Base dos focos VIIRS.
- Breiman, L. (2001). *Random Forests.* Machine Learning, 45, 5–32. [doi:10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324). Modelo de previsão.
- Mavin, A.; Wilkinson, P.; Harwood, A.; Novak, M. (2009). *Easy Approach to Requirements Syntax (EARS).* IEEE
  International Requirements Engineering Conference (RE'09). [doi:10.1109/RE.2009.9](https://doi.org/10.1109/RE.2009.9). Modelo dos requisitos do PRD.
- Documentação: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/), [NASA POWER](https://power.larc.nasa.gov/docs/methodology/) e [NOAA CPC, definição do ONI](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php).
- [GHSL, *GHS-POP R2023A*](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php) (JRC, 2023): método da grade de população.
- **Análise própria** (NASA Space Apps 2026; pipeline em [`infra/`](infra/README.md)):
  - o VIIRS vê 3,8–4,2× mais células-dia de 1 km que o Aqua no Brasil (≈11× à noite);
  - fator por célula de 2° × mês calibrado em 2013–2019 e testado em 2020–2021: MAPE 4,7 % e R² 0,96 no mundo;
  - deriva orbital do Aqua (passagem de 13h38 em 2019 para 14h55 em 2025) e +20 % de detecções em 2024–25, por isso o
    Aqua pós-2021 não entra na calibração;
  - teste de previsão: chuva quase não ajuda a 1 mês; o ONI pesa mais a 3 meses.

## Limites

Não prevê incêndio individual, propagação, área queimada nem severidade. Dados de 2026 só para o Brasil; fora
dele a previsão parte de dez/2025. O POWER cobre a América do Sul. As recomendações apoiam o gestor, não o
substituem.

Detalhes: [front-end](front-end/README.md) · [back-end](back-end/README.md) · [pipeline](infra/README.md) ·
[release](serving/README.md).
