.PHONY: help data verify-data lint test prereg-check check phase1 phase2 report

RUN := uv run

help:
	@echo "make data          fetch raw sources and verify checksums"
	@echo "make verify-data   verify raw checksums only (no network)"
	@echo "make lint          ruff"
	@echo "make test          pytest"
	@echo "make prereg-check  enforce pre-registration ordering"
	@echo "make check         lint + test + prereg-check (what CI runs)"
	@echo "make phase1        steward + Phase 1 reproductions"
	@echo "make phase2        Phase 2 tracks (not yet implemented)"
	@echo "make report        rebuild reports from results/ (not yet implemented)"

data:
	$(RUN) python -m steward.fetch

verify-data:
	$(RUN) python -m steward.fetch --verify

lint:
	$(RUN) ruff check src tests

test:
	$(RUN) pytest

prereg-check:
	$(RUN) python -m redteam.prereg_check

check: lint test prereg-check

phase1:
	@echo "phase1: steward and reproductions not implemented yet (see docs/EXECUTION_PLAN.md §10)" && exit 1

phase2:
	@echo "phase2: not implemented yet" && exit 1

report:
	@echo "report: not implemented yet" && exit 1
