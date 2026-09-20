.PHONY: help lint test test-cov

help:
	@echo "Available targets:"
	@echo "  make lint    Run a Python syntax check across the repo's Python files"
	@echo "  make test     Run the root smoke tests and skill-search tests with unittest"
	@echo "  make test-cov Run the same tests under trace for a line-count summary"

lint:
	python3 -m compileall -q tools skill-search tests

test:
	python3 tools/run_tests.py

test-cov:
	python3 tools/run_tests.py --coverage
