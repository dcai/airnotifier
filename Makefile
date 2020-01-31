
all: start

install-db:
	pipenv run ./install.py

upgrade:
	pipenv run ./upgrade.py

start:
	pipenv run ./app.py

test:
	pipenv run test

format:
	black --exclude "ENV\/|venv\/|venv3.6\/|build/|buck-out/|dist/|_build/|\.eggs/|\.git/|\.hg/|\.mypy_cache/|\.nox/|\.tox/|\.venv/" .

docker-build:
	docker build --tag=airnotifier .

docker-run:
	docker run -p 8088:8088 airnotifier

docker-shell:
	docker run -it --entrypoint /bin/bash airnotifier

docker-start:
	docker-compose up
