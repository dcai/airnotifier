
all: start

install-db:
	pipenv run ./install.py

upgrade:
	pipenv run ./upgrade.py

start:
	pipenv run ./app.py

test:
	pipenv run pytest

format:
	black --exclude "ENV\/|venv\/|venv3.6\/|build/|buck-out/|dist/|_build/|\.eggs/|\.git/|\.hg/|\.mypy_cache/|\.nox/|\.tox/|\.venv/" .
