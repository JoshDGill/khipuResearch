import copy

import pytest
import yaml
from pydantic import ValidationError

from hypotheses.prereg import Prereg, load, load_all
from khipu import paths


def test_all_committed_preregs_validate():
    regs = load_all(paths.PREREG)
    assert {"P1-001", "P1-002", "P1-003"} <= set(regs)


@pytest.fixture
def base():
    return yaml.safe_load((paths.PREREG / "P1-003.yaml").read_text())


def test_accepted_status_is_rejected(tmp_path, base):
    base["status"] = "accepted"
    p = tmp_path / "P1-003.yaml"
    p.write_text(yaml.safe_dump(base))
    with pytest.raises(ValueError, match="human review"):
        load(p)


def test_unknown_keys_rejected(base):
    with pytest.raises(ValidationError):
        Prereg.model_validate({**base, "surprise": 1})


def test_hypothesis_requires_null_models(base):
    h = copy.deepcopy(base)
    h.update(id="H-001", kind="hypothesis", phase=2, tolerance=None,
             multiple_comparisons="BH over ledger", ood_check="coastal -> Inkawasi")
    with pytest.raises(ValidationError, match="null model"):
        Prereg.model_validate(h)
    h["null_models"] = ["shuffle_cord_order", "rule_scramble"]
    Prereg.model_validate(h)


def test_reproduction_requires_tolerance(base):
    with pytest.raises(ValidationError, match="tolerance"):
        Prereg.model_validate({**base, "tolerance": None})
