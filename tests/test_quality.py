import pandas as pd
import pytest

from steward import okr, quality, reconstruction_counts
from steward.crosswalk import OUT_CROSSWALK

pytestmark = pytest.mark.skipif(
    not (okr.OUT_DIR / "khipu_main.parquet").exists() or not OUT_CROSSWALK.exists(),
    reason="run `make steward` first",
)


@pytest.fixture(scope="module")
def table():
    return quality.khipu_table()


@pytest.fixture(scope="module")
def flags(table):
    return quality.flags(table, pd.read_csv(OUT_CROSSWALK))


def test_one_row_per_khipu(table):
    assert table.index.is_unique and len(table) == 619


def test_flags_unique_and_documented_issues_present(flags):
    assert not flags.duplicated(["kh", "flag"]).any()
    got = set(map(tuple, flags[["kh", "flag"]].values))
    assert {("KH0082", "suspect_splice"), ("KH0083", "spacing_unreliable"),
            ("KH0483", "duplicate_record")} <= got


def test_missing_and_partial_are_exclusive(flags):
    for attr in ["ply", "attachment", "colour", "knot_direction"]:
        both = set(flags.kh[flags.flag == f"missing_{attr}"]) & set(
            flags.kh[flags.flag == f"partial_{attr}"])
        assert not both, attr


def test_no_cords_implies_no_knots(flags):
    assert set(flags.kh[flags.flag == "no_cords"]) <= set(flags.kh[flags.flag == "no_knots"])


def test_tiers_are_nested():
    rows, _ = reconstruction_counts.tiers()
    c = {r["tier"]: r["computed"] for r in rows}
    assert c["T2"] >= c["T3"] >= c["T4"] >= c["T5"] > 0
