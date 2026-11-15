COUNTRY ?= ALL
YEARS   ?= 2003-2025
PY      ?= python3

all: data/metrics.json

data/agg/.done:
	$(PY) fetch.py --country $(COUNTRY) --years $(YEARS) --out data/agg && touch $@

data/metrics.json: harmonize.py data/agg/.done
	$(PY) harmonize.py data/agg data

data/ext/oni.ascii.txt:
	mkdir -p data/ext && curl -sSL -o $@ https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

data/agg/viirs-jpss1_2026_Brazil.csv.gz:          # precisa de FIRMS_MAP_KEY; depois rode `make` de novo para harmonizar
	$(PY) fetch_2026.py --out data/agg

# Previsão (RD-04..06) e território (RD-07, RD-09). Entradas IBGE/TI em data/ext (ver territory.py).
data/ext/power_05.parquet:                        # NASA POWER mensal, América do Sul (~2 min)
	$(PY) power.py --out $@

model: data/metrics.json data/ext/oni.ascii.txt data/ext/power_05.parquet
	$(PY) model.py data
	$(PY) territory.py data ../front-end/public/data/countries.geojson

test:
	$(PY) -m unittest discover -s test -v

.PHONY: all test model
