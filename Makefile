.PHONY: run test verify lint format real-data

run:
	PYTHONPATH=src uvicorn feedback_intelligence_engine.main:app --reload

test:
	PYTHONPATH=src pytest --cov=feedback_intelligence_engine --cov-report=term --cov-fail-under=80

verify:
	PYTHONPATH=src python scripts/verify_release.py

lint:
	ruff check src tests scripts

format:
	ruff format src tests scripts

real-data:
	PYTHONPATH=src python scripts/fetch_cfpb_sample.py
