"""Run records: every result folder gets a run.json naming its inputs, seed and prereg IDs."""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from khipu import paths


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(paths.ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_dirty() -> bool:
    out = subprocess.run(
        ["git", "-C", str(paths.ROOT), "status", "--porcelain", "--", "src", "prereg"],
        capture_output=True, text=True,
    )
    return bool(out.stdout.strip())


def seed_everything(seed: int) -> np.random.Generator:
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def start_run(name: str, seed: int, prereg_ids: list[str], inputs: list[Path]) -> Path:
    """Create results/<timestamp>_<name>/ with run.json and return the folder."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    folder = paths.RESULTS / f"{stamp}_{name}"
    folder.mkdir(parents=True, exist_ok=False)
    lock = paths.ROOT / "uv.lock"
    record = {
        "name": name,
        "started_at": stamp,
        "git_sha": git_sha(),
        "git_dirty": git_dirty(),
        "seed": seed,
        "prereg_ids": prereg_ids,
        "uv_lock_sha256": sha256_file(lock) if lock.exists() else None,
        "inputs": {str(p.relative_to(paths.ROOT)): sha256_file(p) for p in inputs},
    }
    (folder / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    return folder
