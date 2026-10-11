"""Download raw sources listed in data/sources.yaml and record them in data/raw/MANIFEST.csv.

Idempotent: files already in the manifest whose sha256 still matches are skipped. A local file
that no longer matches its manifest checksum is an error (raw data must never change in place).

    python -m steward.fetch                 # fetch everything missing, verify the rest
    python -m steward.fetch --only okr kbcr # subset
    python -m steward.fetch --verify        # verify checksums only, no network
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import requests
import yaml

from khipu import paths
from khipu.runlog import sha256_file

FIELDS = [
    "source", "file", "url", "version", "sha256", "bytes", "retrieved_at", "status", "licence",
]
USER_AGENT = "khipuResearch-fetcher/0.1 (+https://github.com/JoshDGill/khipuResearch)"


class ManifestError(RuntimeError):
    pass


def load_manifest() -> dict[tuple[str, str], dict[str, str]]:
    if not paths.MANIFEST.exists():
        return {}
    with open(paths.MANIFEST, newline="") as f:
        return {(r["source"], r["file"]): r for r in csv.DictReader(f)}


def save_manifest(rows: dict[tuple[str, str], dict[str, str]]) -> None:
    paths.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.MANIFEST.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])
    tmp.replace(paths.MANIFEST)


def verify(rows: dict[tuple[str, str], dict[str, str]]) -> list[str]:
    """Return a list of problems; empty means every present file matches the manifest."""
    problems = []
    for (source, name), row in sorted(rows.items()):
        if row["status"] not in ("ok", "extracted"):
            continue
        path = paths.RAW / source / name
        if not path.exists():
            problems.append(f"missing: {source}/{name}")
        elif sha256_file(path) != row["sha256"]:
            problems.append(f"CHECKSUM MISMATCH (raw data changed in place?): {source}/{name}")
    return problems


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def _download(session: requests.Session, url: str, dest: Path) -> int:
    """Download to dest atomically. Returns HTTP status; dest is only written on 200."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=120) as r:
        if r.status_code != 200:
            return r.status_code
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for block in r.iter_content(1 << 20):
                f.write(block)
        tmp.replace(dest)
        return 200


def _record(source: str, name: str, url: str, version: str, licence: str, status: str,
            path: Path | None) -> dict[str, str]:
    return {
        "source": source,
        "file": name,
        "url": url,
        "version": version,
        "sha256": sha256_file(path) if path else "",
        "bytes": str(path.stat().st_size) if path else "",
        "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "licence": licence,
    }


def fetch_file(session, rows, source, spec, entry, delay=0.0) -> bool:
    """Fetch one declared file. Returns True if a network request was made."""
    name, url = entry["name"], entry["url"]
    dest = paths.RAW / source / name
    if (source, name) in rows and rows[(source, name)]["status"] == "ok" and dest.exists():
        return False
    if delay:
        time.sleep(delay)
    status = _download(session, url, dest)
    version, licence = str(spec.get("version", "")), str(spec.get("licence", "")).strip()
    if status != 200:
        rows[(source, name)] = _record(source, name, url, version, licence, f"http_{status}", None)
        print(f"  {source}/{name}: HTTP {status}", file=sys.stderr)
        return True
    if "md5" in entry and _md5(dest) != entry["md5"]:
        dest.unlink()
        raise ManifestError(f"{source}/{name}: md5 does not match the publisher's checksum")
    rows[(source, name)] = _record(source, name, url, version, licence, "ok", dest)
    print(f"  {source}/{name}: ok")
    if entry.get("extract"):
        _extract(rows, source, name, version, licence)
    return True


def _extract(rows, source, zip_name, version, licence) -> None:
    root = paths.RAW / source
    with zipfile.ZipFile(root / zip_name) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            target = (root / info.filename).resolve()
            if root.resolve() not in target.parents:
                raise ManifestError(f"unsafe path in zip: {info.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                while block := src.read(1 << 20):
                    dst.write(block)
            rows[(source, info.filename)] = _record(
                source, info.filename, f"zip:{zip_name}", version, licence, "extracted", target
            )


KFG_ID = re.compile(r"catalog/(KH\d{4}[A-Z]?)\.html")


def fetch_kfg(session, rows, spec) -> None:
    source, delay = "kfg", float(spec.get("crawl_delay_seconds", 10))
    for entry in spec.get("extra_files", []):
        fetch_file(session, rows, source, spec, entry, delay)
    index_entry = {"url": spec["index_url"], "name": "_index/sketchbook_index.html"}
    fetch_file(session, rows, source, spec, index_entry, delay)
    save_manifest(rows)
    index_html = (paths.RAW / source / index_entry["name"]).read_text(errors="replace")
    ids = sorted(set(KFG_ID.findall(index_html)))
    print(f"  kfg index lists {len(ids)} khipus")
    for i, kh in enumerate(ids, 1):
        entry = {"url": spec["file_url_template"].format(kh=kh), "name": f"excel/{kh}.xlsx"}
        if (source, entry["name"]) in rows and rows[(source, entry["name"])]["status"] != "ok":
            continue  # a recorded 404 is a result, not a retry target; use --refresh-failed
        if fetch_file(session, rows, source, spec, entry, delay) and i % 25 == 0:
            save_manifest(rows)
    save_manifest(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--only", nargs="*", help="source ids to fetch (default: all)")
    ap.add_argument("--verify", action="store_true", help="verify checksums only")
    ap.add_argument("--refresh-failed", action="store_true", help="retry entries not marked ok")
    args = ap.parse_args(argv)

    rows = load_manifest()
    problems = verify(rows)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    if args.verify:
        n_ok = sum(r["status"] in ("ok", "extracted") for r in rows.values())
        print(f"manifest ok: {n_ok} files")
        return 0
    if args.refresh_failed:
        rows = {k: v for k, v in rows.items() if v["status"] in ("ok", "extracted")}

    sources = yaml.safe_load(paths.SOURCES_FILE.read_text())
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for source, spec in sources.items():
        if args.only and source not in args.only:
            continue
        print(f"[{source}] {spec['name']} {spec.get('version', '')}")
        if source == "kfg":
            fetch_kfg(session, rows, spec)
        else:
            for entry in spec["files"]:
                fetch_file(session, rows, source, spec, entry)
        save_manifest(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
