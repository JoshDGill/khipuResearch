"""Pre-registration schema (AGENTS.md §6.2, §9.4).

Every test the pipeline runs is declared in prereg/<ID>.yaml and committed before the run.
The schema is deliberately strict: unknown keys are errors, and the pipeline can never set a
status of "accepted" (only the human review gate can accept a claim, outside the pipeline).
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

ID_PATTERN = re.compile(r"^(P\d-\d{3}|H-\d{3})(v\d+)?$")

Status = Literal[
    "registered",  # committed, not yet run
    "run",  # results exist, awaiting red team / gate review
    "reproduced",  # Phase 1 only: inside tolerance, awaiting owner sign-off
    "not_reproduced",  # Phase 1 only: outside tolerance
    "refuted",  # met its refutation criterion
    "failed_redteam",
    "passed_redteam",  # still needs replication (G4) and human review
    "replicated",  # passed G4; goes to the human review packet
    "escalated",  # depends on a single khipu or anchor (stop-and-escalate)
    "withdrawn",  # superseded or abandoned, with reason in notes
]

NullModel = Literal[
    "shuffle_cord_order",
    "shuffle_labels",
    "rule_scramble",
    "plant_rule",
    "alignment_chance",
]


class Tolerance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    published_value: str
    accept_if: str = Field(description="Machine-checkable condition, e.g. '0.69 <= x <= 0.79'")
    rationale: str


class Prereg(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    kind: Literal["reproduction", "hypothesis"]
    phase: Literal[1, 2, 3]
    date: dt.date
    status: Status = "registered"
    supersedes: str | None = None

    claim: str
    sources: list[str] = Field(min_length=1, description="literature the claim comes from")
    features: list[str] = Field(min_length=1)
    data_subset: str
    exclusions: list[str] = Field(default_factory=list)
    definitions: dict[str, str] = Field(default_factory=dict)

    held_out_prediction: str
    refutation_criterion: str
    planned_test: str
    effect_size: str
    tolerance: Tolerance | None = None
    sensitivity_analyses: list[str] = Field(default_factory=list)

    null_models: list[NullModel] = Field(default_factory=list)
    null_models_deferred_to: str | None = None
    multiple_comparisons: str | None = None
    ood_check: str | None = None
    replication: str
    seed: int = 20261011
    notes: str | None = None

    @model_validator(mode="after")
    def _rules(self) -> Prereg:
        if not ID_PATTERN.match(self.id):
            raise ValueError(f"bad id {self.id!r}; use P<phase>-NNN or H-NNN, optional vN suffix")
        if self.kind == "reproduction":
            if self.tolerance is None:
                raise ValueError("reproductions need a tolerance fixed before the run")
            if not self.null_models and not self.null_models_deferred_to:
                raise ValueError("reproductions must list null models or say where they are run")
        else:
            if not self.null_models:
                raise ValueError("hypotheses need at least one null model (AGENTS.md §7)")
            if not self.multiple_comparisons or not self.ood_check:
                raise ValueError("hypotheses need multiple_comparisons and ood_check")
        return self


def load(path: Path) -> Prereg:
    data = yaml.safe_load(path.read_text())
    if isinstance(data, dict) and data.get("status") == "accepted":
        raise ValueError(f"{path.name}: 'accepted' is reserved for the human review gate")
    reg = Prereg.model_validate(data)
    if reg.id != path.stem:
        raise ValueError(f"{path.name}: id {reg.id!r} must match the file name")
    return reg


def load_all(folder: Path) -> dict[str, Prereg]:
    return {p.stem: load(p) for p in sorted(folder.glob("*.yaml"))}
