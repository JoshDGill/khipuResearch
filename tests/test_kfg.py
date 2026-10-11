import pytest

from steward import kfg


def test_parse_group_line():
    assert kfg.parse_group_line("0.0cm group of 11 pendants (1-11) space of 0.17cm") == (1, 11)
    assert kfg.parse_group_line("32.5cm 1 (16)") == (16, 16)
    assert kfg.parse_group_line("!-- Pendant Data") is None


def test_parse_cord_name():
    assert kfg.parse_cord_name("p5") == (5, 1, "")
    assert kfg.parse_cord_name("p12s3s1") == (12, 3, "p12s3")
    assert kfg.parse_cord_name("x1") is None


def test_parse_value():
    assert kfg.parse_value("172") == 172
    assert kfg.parse_value(" 0 ") == 0
    assert kfg.parse_value("1?") is None and kfg.parse_value(None) is None


@pytest.mark.skipif(not (kfg.EXCEL_DIR / "KH0083.xlsx").exists(), reason="KFG not fetched")
def test_load_known_file():
    khipu, groups, cords = kfg.load_file(kfg.EXCEL_DIR / "KH0083.xlsx")
    assert khipu["kh"] == "KH0083" and "UR035" in khipu["aliases"]
    assert groups[0]["first_pendant"] == 1
    assert all(c["src_file"] == "excel/KH0083.xlsx" for c in cords)
