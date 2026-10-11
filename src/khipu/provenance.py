"""Value-level provenance (brief §2.1: every value traceable to its source file and row).

Clean tables carry provenance as plain columns so it survives Parquet round-trips:
``src_source``, ``src_file``, ``src_table`` and ``src_row``. ``Provenance`` is the typed view
used when building those columns.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

PROVENANCE_COLUMNS = ("src_source", "src_file", "src_table", "src_row")


@dataclass(frozen=True)
class Provenance:
    source: str  # source id from data/sources.yaml, e.g. "okr"
    file: str  # path relative to data/raw/<source>/
    table: str  # SQLite table or Excel sheet
    row: str  # primary key or 1-based sheet row, as text

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"Provenance.{name} must be a non-empty string, got {value!r}")

    def columns(self) -> dict[str, str]:
        return {
            "src_source": self.source,
            "src_file": self.file,
            "src_table": self.table,
            "src_row": self.row,
        }


def attach(df: pd.DataFrame, source: str, file: str, table: str, row_col: str) -> pd.DataFrame:
    """Return a copy of ``df`` with provenance columns, taking the row key from ``row_col``."""
    if row_col not in df.columns:
        raise KeyError(f"row key column {row_col!r} not in frame")
    Provenance(source, file, table, "x")  # validate the constant parts
    out = df.copy()
    out["src_source"] = source
    out["src_file"] = file
    out["src_table"] = table
    out["src_row"] = df[row_col].astype(str)
    return out


def assert_complete(df: pd.DataFrame) -> None:
    """Fail if any row lacks provenance. Used by clean-table tests."""
    missing = [c for c in PROVENANCE_COLUMNS if c not in df.columns]
    if missing:
        raise AssertionError(f"missing provenance columns: {missing}")
    blank = df[list(PROVENANCE_COLUMNS)].isna() | (df[list(PROVENANCE_COLUMNS)] == "")
    if blank.any().any():
        bad = int(blank.any(axis=1).sum())
        raise AssertionError(f"{bad} rows have incomplete provenance")
