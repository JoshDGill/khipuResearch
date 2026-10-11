.PHONY: help data verify-data lint test prereg-check check steward phase1 phase2 report

RUN := uv run

help:
	@echo "make data          fetch raw sources and verify checksums"
	@echo "make verify-data   verify raw checksums only (no network)"
	@echo "make lint          ruff"
	@echo "make test          pytest"
	@echo "make prereg-check  enforce pre-registration ordering"
	@echo "make check         lint + test + prereg-check (what CI runs)"
	@echo "make steward       load raw OKR into data/interim/ and write the sentinel report"
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

steward:
	$(RUN) python -m steward.okr
	$(RUN) python -m steward.crosswalk
	$(RUN) python -m steward.kfg
	$(RUN) python -m steward.kfg_published
	$(RUN) python -m steward.quality
	$(RUN) python -m steward.reconstruction_counts

phase1: steward
	@echo "phase1: reproductions not implemented yet (see docs/EXECUTION_PLAN.md §10)" && exit 1

phase2:
	@echo "phase2: not implemented yet" && exit 1

report:
	@echo "report: not implemented yet" && exit 1
