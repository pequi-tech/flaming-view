COUNTRY ?= ALL
YEARS   ?= 2003-2025
PY      ?= python3

all: data/metrics.json

data/agg/.done:
	$(PY) fetch.py --country $(COUNTRY) --years $(YEARS) --out data/agg && touch $@

data/metrics.json: harmonize.py data/agg/.done
	$(PY) harmonize.py data/agg data

test:
	$(PY) -m unittest discover -s test -v

.PHONY: all test
