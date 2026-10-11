import pandas as pd
import pytest

from khipu.provenance import Provenance, assert_complete, attach


def test_provenance_rejects_blank_fields():
    with pytest.raises(ValueError):
        Provenance("okr", "", "cord", "1")


def test_attach_and_assert_complete():
    df = pd.DataFrame({"CORD_ID": [10, 11], "v": [1, 2]})
    out = attach(df, "okr", "data/khipu.db", "cord", "CORD_ID")
    assert list(out["src_row"]) == ["10", "11"]
    assert_complete(out)


def test_assert_complete_catches_gaps():
    df = attach(pd.DataFrame({"k": [1, 2]}), "okr", "f", "t", "k")
    df.loc[1, "src_row"] = ""
    with pytest.raises(AssertionError, match="1 rows"):
        assert_complete(df)
