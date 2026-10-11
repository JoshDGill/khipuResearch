"""Steward step 1: load OKR khipu.db into interim Parquet tables (plan §4.1 step 1).

Values are copied as recorded. Sentinels such as 'U', '', NULL, the string 'null' and the
quoted-blank "''" are kept as distinct values here; they are only mapped to missing in the
clean layer, with a quality flag. Every row gets provenance columns and a ``kh`` column.

    python -m steward.okr          # writes data/interim/okr/*.parquet + the sentinel report
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from khipu import paths
from khipu.provenance import attach

OKR_RELEASE = "open-khipu-repository-2.1.0"
DB_REL = f"{OKR_RELEASE}/data/khipu.db"
KH_LIST_REL = f"{OKR_RELEASE}/data/okr-kh-numbers.csv"

# table -> declared key column. Some declared keys are not unique in the source (for example
# primary_cord.PCORD_ID), so provenance uses the SQLite rowid, which always is, and duplicate
# declared keys are counted in the report instead of being silently dropped.
CORE_TABLES = {
    "khipu_main": "KHIPU_ID",
    "primary_cord": "PCORD_ID",
    "cord": "CORD_ID",
    "cord_cluster": "CLUSTER_ID",
    "knot": "KNOT_ID",
    "knot_cluster": "CLUSTER_ID",
    "ascher_cord_color": "color_id",
}

# Categorical columns whose value inventory goes into the sentinel report.
INVENTORY = {
    "cord": ["TWIST", "ATTACHMENT_TYPE", "FIBER", "TERMINATION", "CORD_LEVEL"],
    "knot": ["TYPE_CODE", "DIRECTION", "NUM_TURNS", "knot_value_type", "AXIS_ORIENTATION"],
    "primary_cord": ["STRUCTURE", "FIBER", "TWIST", "BEGINNING", "TERMINATION"],
    "khipu_main": ["REGION", "DUPLICATE_FLAG", "COMPLETE"],
}

OUT_DIR = paths.INTERIM / "okr"


def db_path() -> Path:
    return paths.RAW / "okr" / DB_REL


def connect() -> sqlite3.Connection:
    p = db_path()
    if not p.exists():
        raise FileNotFoundError(f"{p} missing; run `make data` first")
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def read_table(con: sqlite3.Connection, table: str, rowid: bool = False) -> pd.DataFrame:
    cols = "rowid AS sqlite_rowid, *" if rowid else "*"
    return pd.read_sql_query(f'SELECT {cols} FROM "{table}"', con)


def code_tables(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    names = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%\\_dc' ESCAPE '\\'"
    )]
    return {n: read_table(con, n) for n in sorted(names)}


def kh_map(khipu_main: pd.DataFrame) -> pd.Series:
    m = khipu_main.set_index("KHIPU_ID")["OKR_NUM"]
    if m.index.duplicated().any() or m.isna().any() or m.duplicated().any():
        raise ValueError("khipu_main KHIPU_ID -> OKR_NUM is not a clean 1:1 map")
    return m


def _kh_for(df: pd.DataFrame, table: str, khmap: pd.Series, cord_kh: pd.Series) -> pd.Series:
    if "KHIPU_ID" in df.columns:
        return df["KHIPU_ID"].map(khmap)
    if "CORD_ID" in df.columns:  # knot, knot_cluster carry only CORD_ID
        return df["CORD_ID"].map(cord_kh)
    raise KeyError(f"cannot assign KH number to {table}")


def load(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    raw = {t: read_table(con, t, rowid=True) for t in CORE_TABLES}
    khmap = kh_map(raw["khipu_main"])
    cord_kh = raw["cord"].set_index("CORD_ID")["KHIPU_ID"].map(khmap)
    out = {}
    for table in CORE_TABLES:
        df = raw[table]  # audit columns (CREATED_BY etc.) kept: recorder is a confound covariate
        df.insert(0, "kh", _kh_for(df, table, khmap, cord_kh))
        out[table] = attach(df, "okr", DB_REL, table, "sqlite_rowid")
    return out


def duplicate_keys(tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Number of declared key values that occur more than once, per table."""
    return {
        f"{t}.{pk}": int(tables[t][pk].value_counts().gt(1).sum())
        for t, pk in CORE_TABLES.items()
    }


def _value_label(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "NULL"
    if v == "":
        return "'' (empty)"
    return repr(v) if isinstance(v, str) else str(v)


def inventory(tables: dict[str, pd.DataFrame]) -> list[dict]:
    rows = []
    for table, cols in INVENTORY.items():
        df = tables[table]
        for col in cols:
            counts = df[col].map(_value_label).value_counts()
            for value, n in counts.items():
                rows.append({"table": table, "column": col, "value": value, "count": int(n),
                             "share": round(n / len(df), 4)})
    return rows


def coverage(tables: dict[str, pd.DataFrame], kh_list: pd.DataFrame) -> dict[str, int]:
    km, cord, knot, kc = (tables[t] for t in ("khipu_main", "cord", "knot", "knot_cluster"))
    listed = set(kh_list["OKR Number"].dropna().str.strip())
    with_cords = set(cord["kh"].dropna())
    with_knots = set(knot["kh"].dropna())
    return {
        "khipus": len(km),
        "cords": len(cord),
        "knots": len(knot),
        "khipus_without_cords": int((~km["kh"].isin(with_cords)).sum()),
        "khipus_without_knots": int((~km["kh"].isin(with_knots)).sum()),
        "orphan_knots (CORD_ID not in cord)": int(knot["kh"].isna().sum()),
        "orphan_knot_clusters (CORD_ID not in cord)": int(kc["kh"].isna().sum()),
        "orphan_cords (KHIPU_ID not in khipu_main)": int(cord["kh"].isna().sum()),
        "KH numbers in okr-kh-numbers.csv": len(listed),
        "KH numbers in khipu.db": int(km["kh"].nunique()),
        "in khipu.db but not in the KH list": len(set(km["kh"]) - listed),
        "in the KH list but not in khipu.db": len(listed - set(km["kh"])),
    }


def write_report(inv: list[dict], cov: dict[str, int], dups: dict[str, int], path: Path) -> None:
    lines = [
        "# OKR sentinel and coverage inventory",
        "",
        f"Generated by `python -m steward.okr` from `data/raw/okr/{DB_REL}` (OKR v2.1.0).",
        "Values are shown exactly as recorded. NULL, empty string, the string 'null' and the",
        "quoted blank \"''\" are different raw values; the clean layer decides how each maps to",
        "missing, with a quality flag.",
        "",
        "## Coverage",
        "",
        "| Measure | Count |",
        "|---|---:|",
        *[f"| {k.replace('_', ' ')} | {v:,} |" for k, v in cov.items()],
        "",
        "## Declared keys that are not unique",
        "",
        "Provenance uses the SQLite rowid instead. These rows are kept and resolved in the",
        "clean layer.",
        "",
        "| Key | Duplicated values |",
        "|---|---:|",
        *[f"| `{k}` | {v:,} |" for k, v in dups.items()],
        "",
        "## Value inventory",
        "",
    ]
    df = pd.DataFrame(inv)
    for (table, col), g in df.groupby(["table", "column"], sort=False):
        lines += [f"### `{table}.{col}`", "", "| Value | Count | Share |", "|---|---:|---:|"]
        top = g.sort_values("count", ascending=False)
        for r in top.head(25).itertuples():
            lines.append(f"| {r.value} | {r.count:,} | {r.share:.2%} |")
        if len(top) > 25:
            lines.append(f"| ({len(top) - 25} more values) | {top['count'].iloc[25:].sum():,} | |")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def main() -> int:
    with connect() as con:
        tables = load(con)
        codes = code_tables(con)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
    for name, df in codes.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
    kh_list = pd.read_csv(paths.RAW / "okr" / KH_LIST_REL, dtype=str, encoding="utf-8-sig")
    kh_list.to_parquet(OUT_DIR / "okr_kh_numbers.parquet", index=False)

    cov, dups = coverage(tables, kh_list), duplicate_keys(tables)
    write_report(inventory(tables), cov, dups, paths.REPORTS / "okr_sentinel_inventory.md")
    log = {
        "step": "steward.okr",
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": DB_REL,
        "tables": {k: len(v) for k, v in tables.items()},
        "code_tables": sorted(codes),
        "kh_list_rows": len(kh_list),
        "coverage": cov,
        "duplicate_declared_keys": dups,
    }
    with open(paths.INTERIM / "transform_log.jsonl", "a") as f:
        f.write(json.dumps(log) + "\n")
    print(json.dumps(log["tables"]), json.dumps(cov))
    return 0


if __name__ == "__main__":
    sys.exit(main())
