PYTHON ?= python3
VENV ?= venv

.PHONY: help check-python check-venv install run dev clean

help:
	@printf '%s\n' \
		'VoicePaste make targets:' \
		'  make install [PYTHON=python3]     Create the virtualenv and install deps' \
		'  make run                           Launch VoicePaste from the existing virtualenv' \
		'  make dev                           Run VoicePaste and the Next.js dashboard together' \
		'  make clean                         Remove the virtualenv and logs'

check-python:
	@command -v "$(PYTHON)" >/dev/null 2>&1 || { \
		printf '\nError: could not find %s on your PATH.\n' "$(PYTHON)"; \
		printf 'Install Python 3 first, then rerun one of:\n'; \
		printf '  brew install python\n'; \
		printf '  make install\n'; \
		printf '  make install PYTHON=/path/to/python3\n\n'; \
		exit 1; \
	}

check-venv:
	@if [ ! -x "$(VENV)/bin/python" ]; then \
		printf '\nError: %s is missing.\n' "$(VENV)"; \
		printf 'Create it first with:\n'; \
		printf '  make install\n\n'; \
		exit 1; \
	fi

install: check-python
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -r requirements.txt

run: check-venv
	$(VENV)/bin/python main.py

dev: check-venv
	@trap 'kill 0' EXIT; \
	($(VENV)/bin/python main.py) & \
	(cd voicepaste-app && npm run dev) & \
	wait

clean:
	rm -rf $(VENV) logs/
