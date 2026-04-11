PYTHON ?= python3
VENV   := venv

.PHONY: install run clean

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

run:
	$(VENV)/bin/python main.py

clean:
	rm -rf $(VENV) logs/
