"""Pesos, pisos e cortes do Índice de Prioridade Preventiva (RD-08). Único lugar para mudá-los: o IPP não é materializado."""
WEIGHTS = {'n': 0.50, 'v': 0.25, 'e': 0.25}       # IPP = N^0,5 · V^0,25 · E^0,25
FLOOR = 0.05                                      # nenhum componente zera a prioridade
CUT_QUANTILES = {'medio': 0.50, 'alto': 0.75, 'critico': 0.90}   # quantis globais da release
IPP_LEVELS = ('baixo', 'medio', 'alto', 'critico')
EXPOSED = 0.75                                    # E a partir do qual a população conta como exposta (R2)
RECURRENT = 0.75                                  # V a partir do qual o histórico é recorrente (R6)
