# Flaming View

**Inteligência preditiva para prevenção de incêndios.** Plataforma de apoio à decisão para a Defesa Civil:
prevê onde o fogo tende a se concentrar nos próximos três meses, prioriza territórios pela exposição de pessoas
e terras indígenas e sugere ações preventivas que o gestor aceita ou ignora, com relatório em PDF.

> Protótipo do **NASA Space Apps Challenge 2026**, desafio #8 *Harmonization of MODIS and VIIRS Hot Spots*.
> Não é sistema oficial.

*Prever é o começo. Priorizar é o diferencial. Preparar-se antes é o impacto.*

## Uso de IA

Partes do código, da documentação e do processamento de dados deste projeto foram geradas com auxílio do
**Claude (Anthropic)**, sempre revisadas e testadas pela equipe.

- **Fluxo:** Plan Mode com **Spec-Driven Development**. Primeiro a especificação (PRD), depois o desenho, as tarefas
  e a implementação, cada uma verificada contra a anterior.
- **PRD:** requisitos escritos no modelo **EARS** (*Easy Approach to Requirements Syntax*), com prioridade
  (P0–P5) e critério de aceite verificável para cada um.
- **Revisão:** agentes de IA simularam um especialista de UX/UI e um coordenador de Defesa Civil; os pareceres
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

NASA FIRMS (MODIS, VIIRS S-NPP, NOAA-20) · NASA POWER · NOAA CPC ONI · GHSL POP 2025 (JRC) ·
IBGE malhas e população 2024 · FUNAI terras indígenas (via TerraBrasilis/INPE) · Natural Earth · NASA GIBS.

## Limites

Não prevê incêndio individual, propagação, área queimada nem severidade. Dados de 2026 só para o Brasil; fora
dele a previsão parte de dez/2025. O POWER cobre a América do Sul. As recomendações apoiam o gestor, não o
substituem.

Detalhes: [front-end](front-end/README.md) · [back-end](back-end/README.md) · [pipeline](infra/README.md) ·
[release](serving/README.md).
