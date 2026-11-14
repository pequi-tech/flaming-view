PY    ?= python3
INFRA ?= ../infra/data

publish:
	$(PY) publish.py $(INFRA) release

verify:
	$(PY) publish.py verify release/$$(cat release/CURRENT)

test:
	$(PY) -m unittest discover -s test -v

.PHONY: publish verify test
