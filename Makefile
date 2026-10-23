.PHONY: install app ask eval test lint

install:
	pip install -r requirements-dev.txt

app:
	streamlit run app.py

ask:
	PYTHONPATH=src python -m rag.cli

eval:
	PYTHONPATH=src python -m rag.evaluate

test:
	pytest -q

lint:
	ruff check .
