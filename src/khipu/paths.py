"""Canonical repository paths. Everything resolves from the repo root, never the CWD."""

from __future__ import annotations

import os
from pathlib import Path


def _find_root() -> Path:
    env = os.environ.get("KHIPU_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "AGENTS.md").exists():
            return parent
    raise RuntimeError("Cannot locate repo root; set KHIPU_ROOT")


ROOT = _find_root()
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
CLEAN = DATA / "clean"
ANCHORS = DATA / "anchors"
CONTROLS = DATA / "controls"
PREREG = ROOT / "prereg"
RESULTS = ROOT / "results"
REPORTS = ROOT / "reports"
SOURCES_FILE = DATA / "sources.yaml"
MANIFEST = RAW / "MANIFEST.csv"
