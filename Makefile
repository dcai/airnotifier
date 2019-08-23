
all: install

install:
	python ./install.py

test:
	true

format:
	black --exclude "ENV\/|venv\/|venv3.6\/|build/|buck-out/|dist/|_build/|\.eggs/|\.git/|\.hg/|\.mypy_cache/|\.nox/|\.tox/|\.venv/" .
