"""Pesos, pisos e cortes do Índice de Prioridade Preventiva (RD-08). Único lugar para mudá-los: o IPP não é materializado."""
WEIGHTS = {'n': 0.50, 'v': 0.25, 'e': 0.25}       # IPP = N^0,5 · V^0,25 · E^0,25
FLOOR = 0.05                                      # nenhum componente zera a prioridade
CUT_QUANTILES = {'medio': 0.50, 'alto': 0.75, 'critico': 0.90}   # quantis globais da release
IPP_LEVELS = ('baixo', 'medio', 'alto', 'critico')
EXPOSED = 0.75                                    # E a partir do qual a população conta como exposta (R2)
RECURRENT = 0.75                                  # V a partir do qual o histórico é recorrente (R6)
# N = rank(fogo previsto)^a · rank(previsto ÷ mediana)^(1−a), só entre células com fogo ≥ CUT_MIN_FIRE (resto = piso). Só a razão punha lugares com quase
# nenhum fogo (mas acima do próprio normal) no topo. Calculado no boot sobre a release, sem retreinar.
N_VOLUME_SHARE = 0.75
# Trava de honestidade: "critico" (Máxima) só com fogo previsto acima do normal (classe >= alto). Sem isso, no máximo "alto".
MAX_NEEDS_FIRE = 2
# Cortes Média/Alta/Máxima: quantis só entre células com fogo previsto relevante (células-dia). Com todas as células
# do mundo (metade quase sem fogo), qualquer lugar com algum fogo passava do p75 e quase tudo virava "Alta".
CUT_MIN_FIRE = 0.1
