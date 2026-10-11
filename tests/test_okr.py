"""Steward step 1 tests. Need the OKR raw data (make data); skipped in CI, which has none."""

import pytest

from khipu.provenance import assert_complete
from steward import okr

pytestmark = pytest.mark.skipif(not okr.db_path().exists(), reason="OKR raw data not fetched")


@pytest.fixture(scope="module")
def tables():
    with okr.connect() as con:
        return okr.load(con)


def test_row_counts_match_source(tables):
    with okr.connect() as con:
        for table in okr.CORE_TABLES:
            n = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            assert len(tables[table]) == n, table


def test_every_row_has_provenance(tables):
    for df in tables.values():
        assert_complete(df)
        assert df["src_row"].is_unique


def test_kh_numbers_are_one_to_one(tables):
    km = tables["khipu_main"]
    assert km["kh"].is_unique
    assert km["kh"].str.fullmatch(r"KH\d{4}").all()


def test_every_cord_belongs_to_a_khipu(tables):
    assert tables["cord"]["kh"].notna().all()


def test_sentinels_are_preserved(tables):
    # Raw sentinels must survive loading unchanged; mapping to missing happens in clean.
    twist = set(tables["cord"]["TWIST"].dropna())
    assert {"S", "Z", "U", ""} <= twist
