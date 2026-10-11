"""Enforce pre-registration ordering (AGENTS.md §9.4; plan §7).

Checks, for every prereg file and every results/*/run.json:

1. Every prereg file validates against the schema.
2. Every prereg ID a run names exists.
3. The run was made from a clean tree (``git_dirty`` false) at a commit that already contains
   the prereg file, i.e. the prereg's first commit is an ancestor of (or equal to) the run commit.
4. The prereg's substantive fields at the run commit equal those at first registration. Only
   ``status`` and ``notes`` may change afterwards; anything else needs a new versioned ID with
   ``supersedes``.

Exit status 1 on any violation. Requires full git history (CI: fetch-depth 0).
"""

from __future__ import annotations

import json
import subprocess
import sys

import yaml

from hypotheses.prereg import load_all
from khipu import paths

MUTABLE_FIELDS = {"status", "notes"}


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(paths.ROOT), *args], capture_output=True, text=True)


def first_commit(rel_path: str) -> str | None:
    out = _git("log", "--diff-filter=A", "--format=%H", "--", rel_path).stdout.split()
    return out[-1] if out else None


def content_at(commit: str, rel_path: str) -> dict | None:
    r = _git("show", f"{commit}:{rel_path}")
    return yaml.safe_load(r.stdout) if r.returncode == 0 else None


def _substantive(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in MUTABLE_FIELDS}


def check() -> list[str]:
    errors: list[str] = []
    try:
        regs = load_all(paths.PREREG)
    except Exception as e:  # schema errors are reported, not raised
        return [f"prereg schema: {e}"]

    for run_json in sorted(paths.RESULTS.glob("*/run.json")):
        run = json.loads(run_json.read_text())
        where = run_json.parent.name
        sha = run.get("git_sha", "unknown")
        if run.get("git_dirty"):
            errors.append(f"{where}: run made with uncommitted changes in src/ or prereg/")
        for pid in run.get("prereg_ids", []):
            if pid not in regs:
                errors.append(f"{where}: unknown prereg id {pid}")
                continue
            rel = f"prereg/{pid}.yaml"
            first = first_commit(rel)
            if first is None:
                errors.append(f"{where}: {pid} is not committed")
                continue
            if _git("merge-base", "--is-ancestor", first, sha).returncode != 0:
                errors.append(f"{where}: {pid} was registered after the run commit {sha[:10]}")
                continue
            registered, at_run = content_at(first, rel), content_at(sha, rel)
            if at_run is None or _substantive(registered) != _substantive(at_run):
                errors.append(f"{where}: {pid} changed between registration and run")
    return errors


def main() -> int:
    errors = check()
    for e in errors:
        print(f"PREREG VIOLATION: {e}", file=sys.stderr)
    n_runs = len(list(paths.RESULTS.glob("*/run.json")))
    print(f"prereg-check: {len(list(paths.PREREG.glob('*.yaml')))} preregs, {n_runs} runs, "
          f"{len(errors)} violations")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
