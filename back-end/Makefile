PY   ?= python3
PORT ?= 8000

run:
	$(PY) -m uvicorn app.api:create_app --factory --host 0.0.0.0 --port $(PORT)

test:
	$(PY) -m unittest discover -s tests -t . -v

.PHONY: run test
