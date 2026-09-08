"""Claiming gate floors v1: the GATE-SCHEMA derivation from floors v2.

THRESHOLD BINDING (the pre-registration packet's ceremony step 4 for
``gate_b2_claiming``), NOT A GATE RUN, NOT A RATIFICATION. This script
reads the verified publication floor ``runs/claiming_publication_floor_v1.json``
BY PATH with its size and sha256 pinned, and derives from its committed
strata and trends -- never from typed numbers -- everything the
``gate_b2_claiming`` block needs in the shape ``runs/m4_gate_floors_v1.json``
and ``runs/mortality_gate_floors_v1.json`` established:

* the 42 tolerance derivations in ``Decimal`` under the stated rounding
  mode, each with its unrounded value and its knobs;
* ``gate_partition`` (34 gate-eligible / 8 report-only by the power cap;
  6 disability-conversion cells out of scope);
* beside it, the partition and tolerances under EVERY filed alternative
  (three grammars x K in {1.5, 2.0, 2.5}; K x rounding allowance;
  horizon-aware pricing; ROUND_HALF_EVEN), each cross-checked against the
  floor's own emitted rows, with the deployed-v1 and OLS-full failure
  sets under each -- so a ruling changes a pointer, not a number;
* the rule-class frontier scan as the ``faithful_candidate_oc``
  substitute (C7), the deployed-v1 finding (C8), the certification scope
  (C10 / C11 / C13 / C14), the temporal-holdout circularity disclosure
  (C2 / C3), ``fit_isolation`` naming EVERY committed channel carrying
  the held-out actuals (the three v2 names plus verifier F-A's
  ``scripts/build_ssa_claim_ages.py`` transcription rows, found by scan);
* the eight rulings FILED and PRICED, none made
  (``open_questions_for_the_ceremony``);
* the DRAFT ``gate_b2_claiming`` block as a string
  (``draft_gates_yaml_fragment.text``) with every ruling a placeholder.

It writes NO ``gates.yaml`` byte. It does not open the floor artifact for
writing. It scores no candidate. Run from the repository root::

    .venv/bin/python scripts/build_claiming_gate_floors_v1.py

It needs no PSID, no policyengine-us and no engine.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_claiming_publication_floor as fb  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FLOOR_REL = "runs/claiming_publication_floor_v1.json"
SOURCE_FLOOR_PATH = ROOT / SOURCE_FLOOR_REL
ARTIFACT_REL = "runs/claiming_gate_floors_v1.json"
ARTIFACT_PATH = ROOT / ARTIFACT_REL
EDITION_2023_REL = "data/external/ssa_claim_ages_2023supplement.json"
EDITION_2014_REL = "data/external/ssa_claim_ages_2014supplement.json"
CLAIMING_REFERENCE_REL = "runs/claiming_reference_v1.json"
TRANSCRIPTION_SCRIPT_REL = "scripts/build_ssa_claim_ages.py"
FLOOR_BUILDER_REL = "scripts/build_claiming_publication_floor.py"
GATES_REL = "gates.yaml"

ARTIFACT_SCHEMA_VERSION = "claiming_gate_floors.v1"
RUN_NAME = "claiming_gate_floors_v1"
GATE_NAME = "gate_b2_claiming"
MARKER = "GATE_B2_CLAIMING_BLOCK_LANDED"

#: The VERIFIED floor basis this derivation reads (floors v2 at cd8f167;
#: independent verification VERIFIED -- READY FOR THRESHOLD BINDING).
#: Size and sha256 are pinned here AND in tests/test_gates_derivations.py;
#: a rebuilt floor cannot feed this derivation silently.
SOURCE_FLOOR_COMMITTED = (
    227_079,
    "bd78d632219175d2ab47bc7a87661dde782a6a262a26add3a3be349618593ae1",
)
#: The gates.yaml blob every line citation below is checked against
#: (byte-identical to origin/master at this sitting).
GATES_YAML_BLOB_AT_BINDING = "b0c39af1e13a705f90b85d3e6b9a91e1d3c5485c"

#: The DRAFT knobs, as the floor artifact carries them (asserted equal to
#: the floor's power_cap.knobs at build time; typed here only so the
#: module is readable without the artifact).
K_REV = 2.0
ROUNDING_PP = 0.05
T_MAX_PP = 3.0
TOLERANCE_DECIMALS = 2
TOLERANCE_ROUNDING_MODE = "ROUND_HALF_UP"
K_GRID = (1.5, 2.0, 2.5)
K_SWEEP = (1.5, 2.0, 2.5, 3.0)
ROUNDING_SWEEP = (0.01, 0.05, 0.10)
HORIZONS = (1, 2, 3)
KNIFE_CELL = "age66|female|h1"
TIE_CELL = "age70plus|female|h2"
OUT_OF_SCOPE_REASON = "conversion_flow_owned_by_di_surface"
#: The words the wording audit forbids in the draft block (referee-B R12
#: style; the standing 0 x anchored / aligned rule).
FORBIDDEN_WORDS = ("anchored", "aligned")

_ROUNDING_MODES = {
    "ROUND_HALF_UP": ROUND_HALF_UP,
    "ROUND_HALF_EVEN": ROUND_HALF_EVEN,
}
_QUANTUM = Decimal(1).scaleb(-TOLERANCE_DECIMALS)

PACKET_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "cap-claiming-pia-gates/REPORT.md (104,338 bytes, sha256 "
    "de224e0ccb5a3f7d...)"
)
REFEREE_A_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-referee-A/REPORT.md (47,570 bytes, sha256 "
    "15e614b165bbbfe362e84a6ed372c128a772a153a817cf2e0bbdcf038710a3d0)"
)
REFEREE_B_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-referee-B/REPORT.md (62,507 bytes, sha256 "
    "4f4eebafdcb995ec1386d850b761b13e32afd52f809db31e683b4b897e65ddc9)"
)
FLOORS_V2_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-floors-v2/REPORT.md (49,890 bytes, sha256 "
    "303f077d9967a405e4a9967a8d89c9df909a227fff4d502531f23533351e3ad7)"
)
VERIFICATION_REPORT = (
    "~/m6-sol-lanes/e8-ops/opus-scratch/ceremony-29c03102/"
    "claiming-v2-verify/REPORT.md (66,687 bytes, sha256 "
    "847f29ac0704c18c...)"
)

DOES_NOT_DO = [
    "edit gates.yaml (byte-identical to origin/master; the block lives "
    "only as the string in draft_gates_yaml_fragment.text)",
    "open runs/claiming_publication_floor_v1.json, "
    "runs/claiming_reference_v1.json or either Supplement edition for "
    "writing (each is read by path with its pin checked first)",
    "score a candidate (no candidate is registered on issue #42; the "
    "deployed-v1 and OLS-full failure sets are measurements against a "
    "DRAFT surface, not verdicts)",
    "make any ruling: the eight rulings in open_questions_for_the_ceremony "
    "are FILED and PRICED; the DRAFT surface stays the drafted grammar's "
    "at K_REV 2.0, rounding 0.05, ROUND_HALF_UP, terminal sd on every "
    "horizon until the ratifying round fills the placeholders",
    "ratify any threshold: status draft_pending_referee_round, "
    "locked false, floor_run_sha256 <FILLED AT RATIFICATION>",
    "retire the two live-file 'gate name absent' tests "
    "(tests/test_claiming_publication_floor.py::"
    "test_no_gate_b2_claiming_exists_in_gates_yaml and "
    "tests/test_pia_rule_coverage.py::"
    "test_no_gate_b2_pia_oracle_exists_in_gates_yaml): the flip commit "
    "retires them and flips the pre-lock markers in the same commit",
]

#: gates.yaml line citations the DRAFT block carries, each checked against
#: the pinned blob at build time (line -> a token that line must contain).
GATES_YAML_CITATIONS = {
    565: "no_self_rescue",
    642: "computes exactly",
    1056: "description_claims_exactly_the_scored_surface",
    3294: "description_claims_exactly_the_scored_surface",
    4869: "description_claims_exactly_the_scored_surface",
    3758: "claim-age circularity",
    3760: "blocker 1",
    4359: "circularity_rule",
    4366: "k_vintage",
    4568: "claim_age.age62|female",
}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _sha_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pin(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "sha256": _sha_of_file(path),
        "bytes": path.stat().st_size,
    }


def _git_sha(cwd: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=cwd, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _pinned_gates_yaml() -> bytes:
    """The pinned gates.yaml blob: the working tree while it matches,
    else the git object store."""
    on_disk = (ROOT / GATES_REL).read_bytes()
    if _git_blob_sha1(on_disk) == GATES_YAML_BLOB_AT_BINDING:
        return on_disk
    raw = subprocess.check_output(
        ["git", "cat-file", "blob", GATES_YAML_BLOB_AT_BINDING],
        cwd=ROOT,
        stderr=subprocess.DEVNULL,
    )
    if _git_blob_sha1(raw) != GATES_YAML_BLOB_AT_BINDING:
        raise RuntimeError("git object store returned the wrong blob")
    return raw


def normalized(text: str) -> str:
    """Whitespace-collapsed text: phrase checks must not depend on where
    a folded YAML scalar breaks its lines."""
    return " ".join(text.split())


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def cell_order() -> list[str]:
    """The canonical 42-cell order (female then male; categories in the
    published order; horizons 1..3) -- the packet's and the floor's."""
    return [
        fb._cell_key(category, sex, horizon)
        for sex in fb.SEXES
        for category in fb.CONDITIONAL_CATEGORIES
        for horizon in HORIZONS
    ]


def split_cell(cell: str) -> tuple[str, str, int]:
    category, sex, horizon = cell.split("|")
    return category, sex, int(horizon[1:])


# --------------------------------------------------------------------------
# Inputs, read by path with their pins checked first
# --------------------------------------------------------------------------
def load_source_floor() -> dict[str, Any]:
    """The verified floor, read by path, its bytes checked first."""
    size = SOURCE_FLOOR_PATH.stat().st_size
    digest = _sha_of_file(SOURCE_FLOOR_PATH)
    if (size, digest) != SOURCE_FLOOR_COMMITTED:
        raise RuntimeError(
            f"{SOURCE_FLOOR_REL} is not the verified artifact: "
            f"({size}, {digest}) != {SOURCE_FLOOR_COMMITTED}"
        )
    floor = json.loads(SOURCE_FLOOR_PATH.read_text())
    knobs = floor["power_cap"]["knobs"]
    expected = {
        "k_rev": K_REV,
        "rounding_pp": ROUNDING_PP,
        "t_max_pp": T_MAX_PP,
    }
    for key, value in expected.items():
        if knobs[key] != value:
            raise RuntimeError(f"floor knob {key} = {knobs[key]} != {value}")
    if floor["power_cap"]["rounding_mode"]["mode"] != TOLERANCE_ROUNDING_MODE:
        raise RuntimeError("floor rounding mode is not the drafted one")
    return floor


def load_edition(floor: dict[str, Any]) -> dict[str, Any]:
    """The 2023 edition, read by path, its pin checked against the
    floor's own source pin."""
    pin = _pin(EDITION_2023_REL)
    committed = floor["sources"]["edition_2023"]
    if (pin["sha256"], pin["bytes"]) != (
        committed["sha256"],
        committed["bytes"],
    ):
        raise RuntimeError("the 2023 edition on disk is not the floor's")
    return json.loads((ROOT / EDITION_2023_REL).read_text())


# --------------------------------------------------------------------------
# The derivation: tolerance == quantize(term + |trend| * h + rounding)
# --------------------------------------------------------------------------
def sd_knob_of(floor: dict[str, Any]) -> float:
    """The DRAFT sd knob: the conditional terminal-year population sd of
    the absolute revisions, rounded to 4 decimals."""
    return round(floor["strata"]["conditional_terminal_year"]["sd_pp"], 4)


def trends_of(floor: dict[str, Any]) -> dict[str, float]:
    """Every cell's OLS trend (4 dp) as the floor commits it."""
    derivations = floor["power_cap"]["derivations"]
    return {
        cell: derivations[cell]["trend_pp_per_year"] for cell in cell_order()
    }


def unrounded_tolerance(
    term_pp: float, trend: float, horizon: int, rounding_pp: float
) -> Decimal:
    """The exact decimal sum of the three summands (the floor's
    convention: each knob is the decimal it was written as)."""
    return (
        Decimal(repr(term_pp))
        + Decimal(repr(abs(trend))) * horizon
        + Decimal(repr(rounding_pp))
    )


def quantize(value: Decimal, mode: str) -> float:
    return float(value.quantize(_QUANTUM, rounding=_ROUNDING_MODES[mode]))


def derive_tolerances(
    floor: dict[str, Any],
    *,
    term_by_horizon: dict[int, float] | None = None,
    k_rev: float = K_REV,
    rounding_pp: float = ROUNDING_PP,
    mode: str = TOLERANCE_ROUNDING_MODE,
    t_max_pp: float = T_MAX_PP,
) -> dict[str, dict[str, Any]]:
    """Every cell's tolerance from the FLOOR's strata and trends.

    The revision term defaults to the DRAFT grammar ``K_REV * sd_knob``
    on every horizon; callers price an alternative by passing the term
    per horizon. Nothing is read from a gate artifact.
    """
    sd_knob = sd_knob_of(floor)
    trends = trends_of(floor)
    if term_by_horizon is None:
        term = round(k_rev * sd_knob, 6)
        term_by_horizon = {h: term for h in HORIZONS}
    out: dict[str, dict[str, Any]] = {}
    for cell in cell_order():
        _, _, horizon = split_cell(cell)
        term = term_by_horizon[horizon]
        raw = unrounded_tolerance(term, trends[cell], horizon, rounding_pp)
        tolerance = quantize(raw, mode)
        out[cell] = {
            "trend_pp_per_year": trends[cell],
            "horizon_years": horizon,
            "revision_term_pp": term,
            "rounding_pp": rounding_pp,
            "rounding": TOLERANCE_DECIMALS,
            "rounding_mode": mode,
            "unrounded_tolerance_pp": float(raw),
            "unrounded_tolerance_exact": str(raw),
            "tolerance_pp": tolerance,
            "tolerance_pp_round_half_up": quantize(raw, "ROUND_HALF_UP"),
            "tolerance_pp_round_half_even": quantize(raw, "ROUND_HALF_EVEN"),
            "gate_eligible": tolerance <= t_max_pp,
        }
    return out


def partition_of(
    tolerances: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gated = [c for c in cell_order() if tolerances[c]["gate_eligible"]]
    report = [c for c in cell_order() if not tolerances[c]["gate_eligible"]]
    return {
        "gate_eligible": gated,
        "report_only": report,
        "n_gate_eligible": len(gated),
        "n_report_only": len(report),
        "gate_eligible_tolerances_pp": {
            c: tolerances[c]["tolerance_pp"] for c in gated
        },
        "report_only_tolerance_above_t_max_pp": {
            c: tolerances[c]["tolerance_pp"] for c in report
        },
    }


def check_against_committed(
    derived: dict[str, dict[str, Any]], floor: dict[str, Any]
) -> None:
    """Raise unless every derived tolerance equals the floor's DRAFT
    surface (the synthetic mutation test imports a mutated copy of this
    module and shows this raising)."""
    cap = floor["power_cap"]
    committed = dict(cap["gate_eligible_tolerances_pp"])
    committed.update(
        {
            cell: block["tolerance_pp_would_be"]
            for cell, block in cap["report_only_tolerance_above_t_max"].items()
        }
    )
    mismatches = {
        cell: (derived[cell]["tolerance_pp"], committed[cell])
        for cell in cell_order()
        if derived[cell]["tolerance_pp"] != committed[cell]
    }
    if mismatches:
        raise RuntimeError(
            f"derived tolerances differ from the floor's DRAFT surface on "
            f"{len(mismatches)} cell(s): {mismatches}"
        )
    gated = {c for c in cell_order() if derived[c]["gate_eligible"]}
    if gated != set(cap["gate_eligible_tolerances_pp"]):
        raise RuntimeError("derived partition differs from the floor's")


# --------------------------------------------------------------------------
# The scoring frame (the edition) and the two rules scored under every
# alternative
# --------------------------------------------------------------------------
def scoring_frame(edition: dict[str, Any]) -> dict[str, Any]:
    fit = fb._fit_series(edition, "conditional")
    actuals = fb._actuals(edition, "conditional")
    predictors = fb._candidate_predictors(fit)
    return {"fit": fit, "actuals": actuals, "predictors": predictors}


def score_rule(
    predict, frame: dict[str, Any], gated_tolerances: dict[str, float]
) -> dict[str, Any]:
    """The unrounded-prediction arithmetic of the floor's candidate
    scan: deviation = |predict - actual| (rounded to 4 dp for the
    record; the verdict uses the unrounded value)."""
    deviations: dict[str, float] = {}
    raw: dict[str, float] = {}
    failures: list[str] = []
    margins: dict[str, float] = {}
    for cell in cell_order():
        if cell not in gated_tolerances:
            continue
        category, sex, horizon = split_cell(cell)
        deviation = abs(
            predict(category, sex, horizon)
            - frame["actuals"][(category, sex, horizon)]
        )
        raw[cell] = deviation
        deviations[cell] = round(deviation, 4)
        if deviation > gated_tolerances[cell]:
            failures.append(cell)
            margins[cell] = round(deviation - gated_tolerances[cell], 4)
    values = list(deviations.values())
    return {
        "n_gate_eligible_cells": len(values),
        "n_failed": len(failures),
        "failing_cells": sorted(failures),
        "max_abs_deviation_pp": round(max(raw.values()), 4),
        # the floor's convention: the mean of the 4-dp-ROUNDED per-cell
        # deviations (verifier R2); the unrounded convention beside it.
        "mean_abs_deviation_pp": round(_mean(values), 4),
        "mean_abs_deviation_pp_unrounded_convention": round(
            _mean(list(raw.values())), 4
        ),
        "per_cell_pp": deviations,
        "margin_pp_per_failing_cell": margins,
    }


def failure_sets(
    frame: dict[str, Any], gated_tolerances: dict[str, float]
) -> dict[str, Any]:
    preds = frame["predictors"]
    deployed = score_rule(
        preds["deployed_v1_nearest_year"]["predict"], frame, gated_tolerances
    )
    ols_full = score_rule(
        preds["ols_full_fit_window"]["predict"], frame, gated_tolerances
    )
    return {
        "deployed_v1_nearest_year": {
            k: v for k, v in deployed.items() if k != "per_cell_pp"
        },
        "ols_full_fit_window": {
            k: v for k, v in ols_full.items() if k != "per_cell_pp"
        },
    }


# --------------------------------------------------------------------------
# The alternatives, every one cross-checked against the floor's rows
# --------------------------------------------------------------------------
def _draft_summary(tolerances, frame, draft_gated: dict[str, float]):
    part = partition_of(tolerances)
    gated = part["gate_eligible_tolerances_pp"]
    sets = failure_sets(frame, gated)
    knife = tolerances[KNIFE_CELL]
    ols_dev = sets["ols_full_fit_window"]
    ols_full_predict = frame["predictors"]["ols_full_fit_window"]["predict"]
    knife_ols = round(
        abs(
            ols_full_predict("age66", "female", 1)
            - frame["actuals"][("age66", "female", 1)]
        ),
        4,
    )
    return {
        "n_gate_eligible": part["n_gate_eligible"],
        "n_report_only_tolerance_above_t_max": part["n_report_only"],
        "partition_identical_to_draft": set(gated) == set(draft_gated),
        "cells_demoted_relative_to_draft": sorted(
            set(draft_gated) - set(gated)
        ),
        "cells_promoted_relative_to_draft": sorted(
            set(gated) - set(draft_gated)
        ),
        "n_tolerances_differing_from_draft": sum(
            1
            for cell, tol in gated.items()
            if cell in draft_gated and draft_gated[cell] != tol
        ),
        "deployed_v1_n_failed": sets["deployed_v1_nearest_year"]["n_failed"],
        "deployed_v1_failing_cells": sets["deployed_v1_nearest_year"][
            "failing_cells"
        ],
        "ols_full_fit_window_n_failed": ols_dev["n_failed"],
        "ols_full_fit_window_failing_cells": ols_dev["failing_cells"],
        "age66_female_h1": {
            "gate_eligible": knife["gate_eligible"],
            "tolerance_pp": knife["tolerance_pp"],
            "ols_full_fit_window_deviation_pp": knife_ols,
            "ols_full_fit_window_clears": (
                knife["gate_eligible"] and knife_ols <= knife["tolerance_pp"]
            ),
        },
        "gate_eligible_tolerances_pp": gated,
        "report_only_tolerance_above_t_max_pp": part[
            "report_only_tolerance_above_t_max_pp"
        ],
    }


_FLOOR_ROW_FIELDS = (
    "n_gate_eligible",
    "n_report_only_tolerance_above_t_max",
    "partition_identical_to_draft",
    "cells_demoted_relative_to_draft",
    "cells_promoted_relative_to_draft",
    "n_tolerances_differing_from_draft",
    "deployed_v1_n_failed",
    "deployed_v1_failing_cells",
    "gate_eligible_tolerances_pp",
    "report_only_tolerance_above_t_max_pp",
)


def _cross_check(row: dict[str, Any], floor_row: dict[str, Any]) -> dict:
    """Field-by-field equality against the floor's own emitted row."""
    fields = [f for f in _FLOOR_ROW_FIELDS if f in floor_row]
    mismatches = [f for f in fields if row[f] != floor_row[f]]
    if "age66_female_h1" in floor_row:
        if row["age66_female_h1"] != floor_row["age66_female_h1"]:
            mismatches.append("age66_female_h1")
    if "age66_female_h1_tolerance_pp" in floor_row:
        if (
            row["age66_female_h1"]["tolerance_pp"]
            != floor_row["age66_female_h1_tolerance_pp"]
        ):
            mismatches.append("age66_female_h1_tolerance_pp")
    if mismatches:
        raise RuntimeError(
            f"alternative row differs from the floor: {mismatches}"
        )
    return {
        "fields_compared": fields
        + [
            f
            for f in ("age66_female_h1", "age66_female_h1_tolerance_pp")
            if f in floor_row
        ],
        "equal": True,
    }


def alternatives(
    floor: dict[str, Any], frame: dict[str, Any], draft: dict[str, dict]
) -> dict[str, Any]:
    terminal = floor["strata"]["conditional_terminal_year"]
    settled = floor["strata"]["conditional_settled_years"]
    sd_knob = sd_knob_of(floor)
    mean_abs = terminal["mean_pp"]
    sd_signed_knob = round(terminal["sd_signed_pp"], 4)
    max_abs = terminal["max_pp"]
    settled_knob = round(settled["sd_pp"], 4)
    draft_gated = partition_of(draft)["gate_eligible_tolerances_pp"]
    floor_alt = floor["power_cap_alternatives"]

    grammars = {
        "k_times_sd_abs_DRAFT": (
            "K * sd(|revision|)",
            True,
            lambda k: round(k * sd_knob, 6),
        ),
        "mean_plus_k_times_sd_abs": (
            "mean(|revision|) + K * sd(|revision|) (gate-1's house grammar)",
            False,
            lambda k: round(mean_abs + k * sd_knob, 6),
        ),
        "k_times_sd_signed": (
            "K * sd(signed revision) (== K * RMS; the gate_w1 family-B analogue)",
            False,
            lambda k: round(k * sd_signed_knob, 6),
        ),
        "max_abs_revision_d2": (
            "max(|revision|) (the packet's d2; K does not enter)",
            False,
            lambda k: round(max_abs, 6),
        ),
    }
    by_grammar: dict[str, Any] = {}
    for name, (formula, is_draft, term_of) in grammars.items():
        rows: dict[str, Any] = {}
        for k in K_GRID:
            term = term_of(k)
            tol = derive_tolerances(
                floor, term_by_horizon={h: term for h in HORIZONS}
            )
            row = _draft_summary(tol, frame, draft_gated)
            row["revision_term_pp"] = term
            row["cross_check_against_floor"] = _cross_check(
                row,
                floor_alt["grammar_and_k_sweep"]["by_grammar"][name]["by_k"][
                    f"K_{k}"
                ],
            )
            rows[f"K_{k}"] = row
        by_grammar[name] = {
            "formula": formula,
            "is_the_draft_grammar": is_draft,
            "inputs": {
                "mean_abs_pp": mean_abs,
                "sd_abs_knob_pp": sd_knob,
                "sd_signed_knob_pp": sd_signed_knob,
                "max_abs_pp": max_abs,
            },
            "by_k": rows,
        }

    rounding_rows: dict[str, Any] = {}
    for k in K_SWEEP:
        for rounding_pp in ROUNDING_SWEEP:
            term = round(k * sd_knob, 6)
            tol = derive_tolerances(
                floor,
                term_by_horizon={h: term for h in HORIZONS},
                rounding_pp=rounding_pp,
            )
            row = _draft_summary(tol, frame, draft_gated)
            key = f"K_{k}|rounding_{rounding_pp}"
            row["cross_check_against_floor"] = _cross_check(
                row,
                floor_alt["draft_grammar_k_by_rounding_sweep"]["rows"][key],
            )
            rounding_rows[key] = row

    horizon_terms = {
        1: round(K_REV * settled_knob, 6),
        2: round(K_REV * settled_knob, 6),
        3: round(K_REV * sd_knob, 6),
    }
    horizon_tol = derive_tolerances(floor, term_by_horizon=horizon_terms)
    horizon_row = _draft_summary(horizon_tol, frame, draft_gated)
    horizon_row["revision_term_pp_by_horizon"] = {
        f"h{h}": t for h, t in horizon_terms.items()
    }
    horizon_row["cross_check_against_floor"] = _cross_check(
        horizon_row, floor_alt["horizon_aware_pricing"]["result"]
    )

    half_even = derive_tolerances(floor, mode="ROUND_HALF_EVEN")
    half_even_row = _draft_summary(half_even, frame, draft_gated)
    differing = [
        c
        for c in cell_order()
        if half_even[c]["tolerance_pp"] != draft[c]["tolerance_pp"]
    ]
    half_even_row["cells_differing_from_draft"] = {
        c: {
            "unrounded_tolerance_pp": draft[c]["unrounded_tolerance_pp"],
            "round_half_up_pp": draft[c]["tolerance_pp"],
            "round_half_even_pp": half_even[c]["tolerance_pp"],
        }
        for c in differing
    }
    ties = floor["power_cap"]["rounding_mode"]["exact_ties"]
    if set(differing) != set(ties):
        raise RuntimeError(
            "half-even differs on cells the floor does not name"
        )

    knife_edge = floor["power_cap"]["knife_edge_class"]
    band = Decimal(repr(knife_edge["band_pp"]))
    knife_cells = {}
    for cell in cell_order():
        raw = Decimal(draft[cell]["unrounded_tolerance_exact"])
        scaled = raw / _QUANTUM
        frac = scaled - scaled.to_integral_value(rounding="ROUND_FLOOR")
        distance = abs(frac - Decimal("0.5")) * _QUANTUM
        if distance < band:
            knife_cells[cell] = {
                "unrounded_tolerance_pp": draft[cell][
                    "unrounded_tolerance_pp"
                ],
                "tolerance_pp": draft[cell]["tolerance_pp"],
                "distance_to_boundary_pp": float(distance),
                "is_exact_tie": distance == 0,
                "gate_eligible": draft[cell]["gate_eligible"],
            }
    if set(knife_cells) != set(knife_edge["cells"]):
        raise RuntimeError("knife-edge class differs from the floor's")

    return {
        "purpose": (
            "Every alternative the two adversarial referees priced, "
            "RE-DERIVED here from the floor's strata and trends and "
            "cross-checked field by field against the floor's own emitted "
            "rows (power_cap_alternatives), so that a ruling changes a "
            "pointer in the DRAFT block, not a number. Nothing is chosen."
        ),
        "shared_machinery": floor_alt["shared_machinery"],
        "grammar_and_k_sweep": {
            "k_values": list(K_GRID),
            "rounding_pp": ROUNDING_PP,
            "by_grammar": by_grammar,
        },
        "draft_grammar_k_by_rounding_sweep": {
            "k_values": list(K_SWEEP),
            "rounding_values_pp": list(ROUNDING_SWEEP),
            "rows": rounding_rows,
        },
        "horizon_aware_pricing": {
            "derivation": floor_alt["horizon_aware_pricing"]["derivation"],
            "knobs": {
                "k_rev": K_REV,
                "revision_sd_h1_h2_pp": settled_knob,
                "revision_sd_h3_pp": sd_knob,
                "rounding_pp": ROUNDING_PP,
                "t_max_pp": T_MAX_PP,
            },
            "result": horizon_row,
        },
        "rounding_mode_round_half_even": {
            "derivation": (
                "the DRAFT grammar, K_REV and rounding allowance with the "
                "quantisation mode ROUND_HALF_EVEN instead of ROUND_HALF_UP; "
                "the two differ only on an exact 2-decimal tie"
            ),
            "result": half_even_row,
            "n_cells_differing_from_draft": len(differing),
        },
        "knife_edge_class": {
            "band_pp": knife_edge["band_pp"],
            "definition": knife_edge["definition"],
            "n_cells": len(knife_cells),
            "n_gate_eligible": sum(
                1 for v in knife_cells.values() if v["gate_eligible"]
            ),
            "cells": knife_cells,
        },
        "every_row_cross_checked_against_the_floor": True,
    }


# --------------------------------------------------------------------------
# C7 -- the rule-class frontier scan as the faithful_candidate_oc substitute
# --------------------------------------------------------------------------
def _envelope(
    frame: dict[str, Any], names, gated_tolerances: dict[str, float]
) -> dict[str, Any]:
    preds = frame["predictors"]
    per_cell: dict[str, float] = {}
    for cell in cell_order():
        if cell not in gated_tolerances:
            continue
        category, sex, horizon = split_cell(cell)
        per_cell[cell] = min(
            abs(
                preds[name]["predict"](category, sex, horizon)
                - frame["actuals"][(category, sex, horizon)]
            )
            for name in names
        )
    failures = sorted(
        c for c, v in per_cell.items() if v > gated_tolerances[c]
    )
    argmax = max(per_cell, key=per_cell.get)
    return {
        "rules_in_envelope": sorted(names),
        "n_rules": len(names),
        "n_failed": len(failures),
        "failing_cells": failures,
        "max_abs_deviation_pp": round(max(per_cell.values()), 4),
        "argmax_cell": argmax,
        "mean_abs_deviation_pp": round(_mean(list(per_cell.values())), 4),
        "per_cell_pp": {c: round(v, 4) for c, v in per_cell.items()},
    }


def frontier_scan(
    floor: dict[str, Any], frame: dict[str, Any], gated: dict[str, float]
) -> dict[str, Any]:
    committed = floor["candidate_rules_on_the_draft_surface"]
    preds = frame["predictors"]
    rules: dict[str, Any] = {}
    mean_convention: dict[str, Any] = {}
    for name, spec in preds.items():
        scored = score_rule(spec["predict"], frame, gated)
        committed_rule = committed["rules"][name]
        for field in ("n_failed", "failing_cells", "max_abs_deviation_pp"):
            if scored[field] != committed_rule[field]:
                raise RuntimeError(
                    f"rule {name}.{field} differs from the floor"
                )
        # R2: the floor's per-rule mean is the mean of the 4-dp-ROUNDED
        # per-cell deviations; the envelopes' means are unrounded.
        rounded_mean = scored["mean_abs_deviation_pp"]
        unrounded_mean = scored["mean_abs_deviation_pp_unrounded_convention"]
        if rounded_mean != committed_rule["mean_abs_deviation_pp"]:
            raise RuntimeError(f"rule {name} mean convention mismatch")
        mean_convention[name] = {
            "mean_of_4dp_rounded_per_cell_deviations_pp": rounded_mean,
            "mean_of_unrounded_per_cell_deviations_pp": unrounded_mean,
            "floor_artifact_carries": committed_rule["mean_abs_deviation_pp"],
            "differ_by_one_ulp": rounded_mean != unrounded_mean,
        }
        rules[name] = {
            "rule_class": spec["rule_class"],
            "description": spec["description"],
            "n_failed": scored["n_failed"],
            "failing_cells": scored["failing_cells"],
            "max_abs_deviation_pp": scored["max_abs_deviation_pp"],
            "mean_abs_deviation_pp_4dp_rounded_convention": rounded_mean,
            "mean_abs_deviation_pp_unrounded_convention": unrounded_mean,
        }
    forecast = sorted(
        n for n, s in preds.items() if s["rule_class"] == "forecast"
    )
    envelopes = {
        "post_hoc_best_of_forecast_class_envelope": _envelope(
            frame, forecast, gated
        ),
        "envelope_at_the_packet_window_grid": _envelope(
            frame, fb.PACKET_WINDOW_GRID_FORECAST_RULES, gated
        ),
        "envelope_over_the_v1_eleven_rules_including_degenerate": _envelope(
            frame, fb.V1_ELEVEN_RULES, gated
        ),
        "envelope_over_all_rules_including_degenerate": _envelope(
            frame, tuple(preds), gated
        ),
    }
    for name, env in envelopes.items():
        for field in (
            "n_failed",
            "failing_cells",
            "max_abs_deviation_pp",
            "mean_abs_deviation_pp",
            "per_cell_pp",
            "argmax_cell",
        ):
            if env[field] != committed[name][field]:
                raise RuntimeError(f"envelope {name}.{field} differs")
    sweep = committed["ols_window_sweep"]
    windows: dict[str, Any] = {}
    for window in range(2, 23):
        values = {}
        for cell in gated:
            category, sex, horizon = split_cell(cell)
            years = fb.FIT_YEARS[-window:]
            slope, intercept = fb._ols_slope(
                years, frame["fit"][(category, sex)][-window:]
            )
            predicted = intercept + slope * (fb.FIT_YEARS[-1] + horizon)
            values[cell] = abs(
                predicted - frame["actuals"][(category, sex, horizon)]
            )
        failures = sorted(c for c, v in values.items() if v > gated[c])
        row = sweep["rows"][f"ols_last_{window}"]
        if failures != row["failing_cells"]:
            raise RuntimeError(f"ols window {window} differs from the floor")
        windows[f"ols_last_{window}"] = {
            "window_years": window,
            "n_failed": len(failures),
            "age66_female_h1_deviation_pp": round(values[KNIFE_CELL], 4),
            "age66_female_h1_clears": values[KNIFE_CELL] <= gated[KNIFE_CELL],
        }
    clearing = sorted(
        w["window_years"]
        for w in windows.values()
        if w["age66_female_h1_clears"]
    )
    if clearing != sweep["windows_clearing_age66_female_h1"]:
        raise RuntimeError("clearing windows differ from the floor")
    return {
        "method": (
            "A deterministic rule has no seed and therefore no operating "
            "characteristic in the gate_m4 sense (faithful_candidate_oc, "
            "gates.yaml:3206-3220). The substitute the packet's C7 names "
            "is a rule-class frontier scan: every named rule, fit on "
            "1998-2019 ONLY, scored on the 34 DRAFT gate-eligible cells "
            "with the unrounded-prediction arithmetic; the post-hoc "
            "per-cell envelope over the forecast class bounds the "
            "frontier of THIS enumeration and is not prospectively "
            "achievable. It is a scan, not a proof: the class admits "
            "every fit window (ols_window_sweep) and estimators not "
            "enumerated (Holt, log-share OLS, cross-sex borrowing)."
        ),
        "surface": committed["surface"],
        "rule_classes": committed["rule_classes"],
        "n_rules": len(rules),
        "n_forecast_rules": len(forecast),
        "rules": rules,
        **envelopes,
        "ols_window_sweep": {
            "definition": sweep["definition"],
            "age66_female_h1_tolerance_pp": gated[KNIFE_CELL],
            "windows_clearing_age66_female_h1": clearing,
            "windows_in_packet_grid_clearing_age66_female_h1": sorted(
                w for w in clearing if w in (3, 5, 10, 22)
            ),
            "windows_with_zero_failures_on_all_34": sorted(
                w["window_years"]
                for w in windows.values()
                if w["n_failed"] == 0
            ),
            "best_single_window_by_n_failed": min(
                windows, key=lambda n: (windows[n]["n_failed"], n)
            ),
            "rows": windows,
        },
        "every_gate_eligible_cell_failed_by_some_rule": sorted(gated)
        == sorted({c for r in rules.values() for c in r["failing_cells"]}),
        "per_rule_mean_convention_R2": {
            "statement": (
                "the floor artifact's candidate_rules_on_the_draft_surface."
                "rules[*].mean_abs_deviation_pp is the mean of the "
                "4-decimal-ROUNDED per-cell deviations; the four envelope "
                "means are means of UNROUNDED per-cell values. Both are "
                "emitted per rule here; they differ by one 4-dp ulp on the "
                "rules listed (verifier R2). The floor artifact is not "
                "re-emitted."
            ),
            "rules_where_the_two_conventions_differ": sorted(
                n for n, v in mean_convention.items() if v["differ_by_one_ulp"]
            ),
            "by_rule": mean_convention,
        },
        "reading": (
            "the deployed rule fails 6 of 34; shapeless / level-only / "
            "sex-blind rules fail 31 / 23 / 8; the best single OLS window "
            "fails 1 (ols_last_6) and the best named rules 2 (ols_last_5, "
            "damped_local_trend_w5_d1.0); the packet-grid envelope fails "
            "exactly age66|female|h1 (2.3288 vs 2.24) and the widened "
            "envelope fails nothing (max 1.2519). The surface is neither "
            "vacuous nor a wall for a single rule."
        ),
        "recomputed_here_and_equal_to_the_floor": True,
    }


def deployed_finding(
    floor: dict[str, Any], frame: dict[str, Any], gated: dict[str, float]
) -> dict[str, Any]:
    scored = score_rule(
        frame["predictors"]["deployed_v1_nearest_year"]["predict"],
        frame,
        gated,
    )
    committed = floor["deployed_v1_finding"]
    if scored["failing_cells"] != committed["failing_cells"]:
        raise RuntimeError("deployed failure set differs from the floor")
    per_cell = {}
    for cell in scored["failing_cells"]:
        block = committed["per_failing_cell"][cell]
        if (
            scored["per_cell_pp"][cell] != block["deviation_pp"]
            or scored["margin_pp_per_failing_cell"][cell] != block["margin_pp"]
        ):
            raise RuntimeError(f"deployed cell {cell} differs from the floor")
        per_cell[cell] = {
            "deviation_pp": scored["per_cell_pp"][cell],
            "tolerance_pp": gated[cell],
            "margin_pp": scored["margin_pp_per_failing_cell"][cell],
            "reference_pp": block["reference_pp"],
            "tolerance_in_knife_edge_class": block[
                "tolerance_in_knife_edge_class"
            ],
        }
    return {
        "reported_not_gated": True,
        "statement": committed["statement"],
        "n_gate_eligible_cells": scored["n_gate_eligible_cells"],
        "n_failed": scored["n_failed"],
        "failing_cells": scored["failing_cells"],
        "max_abs_deviation_pp": scored["max_abs_deviation_pp"],
        "mean_abs_deviation_pp": scored["mean_abs_deviation_pp"],
        "mean_abs_deviation_pp_unrounded_convention": scored[
            "mean_abs_deviation_pp_unrounded_convention"
        ],
        "per_failing_cell": per_cell,
        "margin_arithmetic": committed["margin_arithmetic"],
        "reading_C8": (
            "Disclosed at proposal time, not discovered by a referee: "
            "adopting the gate as drafted means the CURRENTLY DEPLOYED "
            "nearest-year rule does not pass it. Whether that is "
            "acceptable bite or evidence of mis-pricing is the referee "
            "round's C8; under both house grammars at K 2.0 the same rule "
            "fails 4 cells, and under horizon-aware pricing 15 -- every "
            "alternative is priced in `alternatives` so the answer reads "
            "bytes."
        ),
        "recomputed_here_and_equal_to_the_floor": True,
    }


# --------------------------------------------------------------------------
# Fit isolation (F-A) -- every committed channel carrying the held-out rows
# --------------------------------------------------------------------------
def _tracked_text_files() -> list[Path]:
    listed = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).split("\n")
    keep = []
    for rel in listed:
        if not rel:
            continue
        if rel.endswith(
            (
                ".png",
                ".pdf",
                ".pkl",
                ".parquet",
                ".zip",
                ".gz",
                ".h5",
                ".jpg",
                ".svg",
                ".ico",
                ".woff",
                ".woff2",
            )
        ):
            continue
        keep.append(ROOT / rel)
    return keep


def _raw_row_signature(row: dict[str, Any], year: int, columns) -> str:
    """The tab-separated row as the 2023 edition's transcription script
    embeds it: year, count with a thousands separator, average age,
    100.0, then the twelve raw columns with '. . .' for null."""
    values = [
        str(year),
        f"{row['number_thousands']:,}",
        f"{row['average_age']:.1f}",
        f"{row['published_total']:.1f}",
    ]
    for column in columns:
        v = row["raw"][column]
        values.append(". . ." if v is None else f"{v:.1f}")
    return "\t".join(values)


def fit_isolation(
    floor: dict[str, Any], edition: dict[str, Any]
) -> dict[str, Any]:
    columns = edition["column_schema"]["raw_columns"]
    holdout_years = (2020, 2021, 2022)
    signatures: dict[str, dict[str, str]] = {}
    for sex in fb.SEXES:
        for year in holdout_years:
            row = edition["data"][sex][str(year)]
            cond = fb.conditional_shares(row)
            signatures[f"{sex}|{year}"] = {
                "conditional_4dp": [
                    f"{round(cond[c], 4)}" for c in fb.CONDITIONAL_CATEGORIES
                ],
                "raw_tab_row": _raw_row_signature(row, year, columns),
                "json_categories": [
                    f'"{c}": {row["categories"][c]}'
                    for c in fb.PUBLISHED_CATEGORIES
                ],
            }
    hits: dict[str, dict[str, list[str]]] = {
        "conditional_4dp": {},
        "raw_tab_row": {},
        "json_categories": {},
    }
    skipped: list[str] = []
    n_scanned = 0
    for path in _tracked_text_files():
        rel = str(path.relative_to(ROOT))
        if path.resolve() == ARTIFACT_PATH.resolve():
            continue
        try:
            if path.stat().st_size > 50_000_000:
                skipped.append(rel)
                continue
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(rel)
            continue
        n_scanned += 1
        for key, sig in signatures.items():
            if all(token in body for token in sig["conditional_4dp"]):
                hits["conditional_4dp"].setdefault(rel, []).append(key)
            if sig["raw_tab_row"] in body:
                hits["raw_tab_row"].setdefault(rel, []).append(key)
            if all(token in body for token in sig["json_categories"]):
                hits["json_categories"].setdefault(rel, []).append(key)
    # The transcription script's row lines (verifier F-A), by line number.
    script = (ROOT / TRANSCRIPTION_SCRIPT_REL).read_text().splitlines()
    script_lines: dict[str, list[int]] = {}
    for key, sig in signatures.items():
        script_lines[key] = [
            i + 1
            for i, line in enumerate(script)
            if sig["raw_tab_row"] in line
        ]
    if any(len(v) != 1 for v in script_lines.values()):
        raise RuntimeError(
            f"transcription rows not found once each: {script_lines}"
        )
    male_lines = sorted(script_lines[f"male|{y}"][0] for y in holdout_years)
    female_lines = sorted(
        script_lines[f"female|{y}"][0] for y in holdout_years
    )
    v2_channels = floor["fit_isolation"][
        "channels_carrying_the_held_out_actuals"
    ]
    channels = [dict(c) for c in v2_channels]
    channels.append(
        {
            "path": TRANSCRIPTION_SCRIPT_REL,
            "fields": [
                f"RAW_TABLE lines {male_lines[0]}-{male_lines[-1]} (male 2020-2022)",
                f"RAW_TABLE lines {female_lines[0]}-{female_lines[-1]} (female 2020-2022)",
            ],
            "pin": _pin(TRANSCRIPTION_SCRIPT_REL),
            "line_numbers": {"male": male_lines, "female": female_lines},
            "note": (
                "verifier finding F-A: the 2023 edition's verbatim "
                "transcription, the source the named edition JSON is built "
                "from; carries no information the edition lacks, but it is "
                "a committed copy of the 2020-2022 rows and the DRAFT's "
                "fit_isolation must name it"
            ),
        }
    )
    named = {c["path"] for c in channels}
    found = set()
    for by_file in hits.values():
        found.update(by_file)
    unnamed = sorted(found - named)
    return {
        "purpose": floor["fit_isolation"]["purpose"],
        "channels_carrying_the_held_out_actuals": channels,
        "n_channels": len(channels),
        "scan": {
            "method": (
                "every git-tracked text file (binary extensions skipped) "
                "searched for three signatures of each of the six held-out "
                "(sex, entitlement year) rows: (a) all seven 4-dp "
                "conditional shares of the row, (b) the row's tab-separated "
                "transcription line, (c) all eight JSON category pairs of "
                "the row; this artifact excluded from its own scan"
            ),
            "n_files_scanned": n_scanned,
            "files_skipped": skipped,
            "hits_by_signature": hits,
            "files_hit": sorted(found),
            "files_hit_not_named_as_a_channel": unnamed,
            "every_hit_is_a_named_channel": not unnamed,
        },
        "consequence": floor["fit_isolation"]["consequence"],
        "required_draft_clause": (
            "gate_b2_claiming.protocol.fit_isolation must name the 2023 "
            "edition and EVERY committed copy of its 2020-2022 rows -- "
            "runs/claiming_publication_floor_v1.json, "
            "runs/claiming_reference_v1.json, "
            "data/external/ssa_claim_ages_2023supplement.json and "
            f"{TRANSCRIPTION_SCRIPT_REL} (lines "
            f"{male_lines[0]}-{male_lines[-1]}, "
            f"{female_lines[0]}-{female_lines[-1]}) -- and this artifact "
            "itself once committed; the registration must fix the rule "
            "class and fit window before scoring."
        ),
    }


# --------------------------------------------------------------------------
# gates.yaml citations, checked against the pinned blob
# --------------------------------------------------------------------------
def gates_yaml_citations() -> dict[str, Any]:
    raw = _pinned_gates_yaml()
    lines = raw.decode("utf-8").split("\n")
    checks = {}
    for line_no, token in GATES_YAML_CITATIONS.items():
        text = lines[line_no - 1]
        if token not in text:
            raise RuntimeError(
                f"gates.yaml:{line_no} does not contain {token!r}: {text!r}"
            )
        checks[str(line_no)] = {"expects": token, "holds": True}
    body = raw.decode("utf-8")
    return {
        "git_blob_sha1": GATES_YAML_BLOB_AT_BINDING,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "byte_identical_to_working_tree": raw
        == (ROOT / GATES_REL).read_bytes(),
        "line_citations": checks,
        "gate_b2_claiming_present": "gate_b2_claiming" in body,
        "gate_b2_pia_oracle_present": "gate_b2_pia_oracle" in body,
        "artifact_named": ARTIFACT_REL in body,
        "floor_named": SOURCE_FLOOR_REL in body,
        "pin_semantics": (
            "PROVENANCE of the line citations in the DRAFT block only; NOT "
            "a freeze of the live file. The two live-file 'gate name "
            "absent' tests read the working tree by design."
        ),
    }


# --------------------------------------------------------------------------
# Certification scope, circularity disclosure, rulings
# --------------------------------------------------------------------------
def certification_scope(floor: dict[str, Any], part: dict[str, Any]) -> dict:
    scope = floor["power_cap"]["out_of_module_scope"]
    return {
        "tranche": "b2_claiming_age_distribution",
        "headline": (
            "if ratified, a PASS certifies that a candidate claiming RULE "
            "reproduces the CONDITIONAL claim-age distribution of "
            "retired-worker awardees, by sex, on the three Supplement "
            "entitlement years it has not read (2020, 2021, 2022), at "
            "horizons 1-3 years past its fit window (1998-2019), on "
            f"EXACTLY the {part['n_gate_eligible']} gate-eligible cells, "
            "within a publication-revision-priced tolerance. Nothing else."
        ),
        "horizon_C11": {
            "priced_horizons_years": list(HORIZONS),
            "entitlement_years_scored": {"h1": 2020, "h2": 2021, "h3": 2022},
            "last_fit_year": fb.FIT_YEARS[-1],
            "deployment_note": (
                "gate_w1 deploys at anchor_frame_year 2024 with "
                "claim_age_delta_years 2 (gates.yaml:4366-4368), i.e. h = 2 "
                "and growing by one each frame year; a 2030+ frame is "
                "outside anything this gate prices. Extrapolation beyond "
                "h = 3 is NOT certified."
            ),
        },
        "scored_surface_C13": {
            "gate_eligible_cells": part["gate_eligible"],
            "report_only_tolerance_above_t_max": part["report_only"],
            "claims_exactly_the_scored_surface": (
                "the standing rule description_claims_exactly_the_scored_"
                "surface (gates.yaml:1056, :3294, :4869): covers / "
                "holdout_basis / estimand claim EXACTLY these cells -- no "
                "claiming behaviour outside entitlement years 2020-2022, no "
                "horizon beyond h = 3, no benefit LEVEL, no "
                "disability-conversion flow, and no multi-cohort reading "
                "(expected_reduction_factor is documented as a SINGLE-COHORT "
                "reading, claiming.py:396-405, and nothing here certifies it)"
            ),
        },
        "out_of_scope_C10": {
            "cells": scope["cells"],
            "reason": scope["reason"],
            "basis": scope["basis"],
            "excluded_by": "SCOPE, before any candidate runs; not power, not "
            "candidate performance",
        },
        "what_a_pass_authorises_C14": {
            "supports": [
                "the #74 CA (claiming) component for the claiming / "
                "mortality-dependent provision class on the OBSERVED frame, "
                "at h <= 3 from the 2023 edition's last fit year",
                "an ARGUMENT for a gate_w1 amendment de-circularising family "
                "B's 14 report-only claim-age cells (gates.yaml:4568-4573): a "
                "candidate certified on a temporal holdout is no longer 'the "
                "module that samples from the anchor it is scored against'",
            ],
            "does_not_authorise": [
                "re-gating gate_w1's 14 report-only claim-age cells by itself: "
                "that needs a gate_w1 amendment with its own ceremony "
                "(public proposal + referee round + verification + ratifying "
                "merge); this gate makes such an amendment arguable and does "
                "not make it",
                "any benefit LEVEL: the 402(q)/(w) factors the module "
                "multiplies through (claiming.py:360-376) are the oracle's "
                "and belong to gate_b2_pia_oracle",
                "extrapolation beyond h = 3",
                "the disability-conversion flow (owned by the DI surface) or "
                "the multi-cohort composition of an entitlement year",
                "the SSA claiming PROCESS: the estimand is the published "
                "conditional share vector, not behaviour",
            ],
        },
    }


def circularity_disclosure() -> dict[str, Any]:
    return {
        "C2_is_the_holdout_a_holdout": {
            "mechanism": (
                "the module's loader caches the WHOLE reference document "
                "(_load_cached, claiming.py:169-179); an in-range request "
                "is an exact lookup that returns the held-out row verbatim "
                "(_resolve_year, :200-213; ref.row, :230). Passing the full "
                "document and promising not to look is therefore NOT a "
                "holdout."
            ),
            "requirement": (
                "a candidate run is handed a reference object PHYSICALLY "
                "restricted to entitlement years 1998-2019; a run whose "
                "candidate had access to a 2020-2022 row is INVALIDATED and "
                "must be re-registered (protocol.fit_isolation)"
            ),
        },
        "C3_does_the_temporal_holdout_de_circularise": {
            "the_finding_it_answers": (
                "gate_w1 round-1 blocker 1 (gates.yaml:3758-3761) and the "
                "ratified circularity_rule (:4359-4365): the deployed v1 "
                "claiming module samples integer claim ages FROM 6.B5.1, so "
                "scoring it against 6.B5.1 passes by construction; the 14 "
                "non-conversion claim-age cells are report-only (:4568-4573)"
            ),
            "why_fitting_to_1998_2019_escapes_it": (
                "a candidate fit on 1998-2019 and scored on 2020-2022 has "
                "never read the scored rows; the prediction is an "
                "out-of-sample statement about a table the candidate cannot "
                "see, in the same sense gate 1 holds out persons"
            ),
            "why_in_window_reproduction_stays_report_only": (
                "reproduction of 1998-2019 is a lookup of the file the "
                "candidate was fit on and passes by construction; it is "
                "published as an integrity check and NEVER gated"
            ),
            "residual_circularity_disclosed": (
                "physical isolation is impossible for public data and for an "
                "artifact that publishes every held-out actual and every "
                "tolerance (fit_isolation names every committed channel). "
                "The defence is procedural: rule class and fit window "
                "registered on issue #42 before scoring, one shot, "
                "no_self_rescue; the frontier scan here is post hoc and says "
                "so -- the moment one of its rules is registered as a "
                "candidate, its scores here are prior knowledge."
            ),
        },
    }


def open_questions(
    floor: dict[str, Any], alt: dict[str, Any], scan: dict[str, Any]
) -> list[dict[str, Any]]:
    g = alt["grammar_and_k_sweep"]["by_grammar"]

    def row(grammar: str, k: float) -> dict[str, Any]:
        r = g[grammar]["by_k"][f"K_{k}"]
        return {
            "partition": f"{r['n_gate_eligible']} / "
            f"{r['n_report_only_tolerance_above_t_max']}",
            "deployed_v1_n_failed": r["deployed_v1_n_failed"],
            "ols_full_fit_window_n_failed": r["ols_full_fit_window_n_failed"],
            "age66_female_h1_tolerance_pp": r["age66_female_h1"][
                "tolerance_pp"
            ],
            "ols_full_clears_age66_female_h1": r["age66_female_h1"][
                "ols_full_fit_window_clears"
            ],
        }

    rs = alt["draft_grammar_k_by_rounding_sweep"]["rows"]
    horizon = alt["horizon_aware_pricing"]["result"]
    half_even = alt["rounding_mode_round_half_even"]
    knife = alt["knife_edge_class"]
    packet_env = scan["envelope_at_the_packet_window_grid"]
    widened_env = scan["post_hoc_best_of_forecast_class_envelope"]
    sweep = scan["ols_window_sweep"]
    od = floor["open_decisions"]
    return [
        {
            "id": "1",
            "name": "grammar_and_k_rev",
            "question": od["grammar_and_k_rev"]["question"],
            "table": "alternatives.grammar_and_k_sweep (each row cross-checked against the floor's power_cap_alternatives)",
            "priced": {
                grammar: {f"K_{k}": row(grammar, k) for k in K_GRID}
                for grammar in g
            },
            "k_by_rounding": {
                key: {
                    "partition": f"{r['n_gate_eligible']} / "
                    f"{r['n_report_only_tolerance_above_t_max']}",
                    "deployed_v1_n_failed": r["deployed_v1_n_failed"],
                }
                for key, r in rs.items()
            },
            "what_moves": od["grammar_and_k_rev"]["what_moves"],
            "draft_stays": od["grammar_and_k_rev"]["draft_stays"],
            "placeholder_in_block": "<RULING 1 grammar_and_k_rev>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "2",
            "name": "horizon_pricing",
            "question": od["horizon_pricing"]["question"],
            "table": "alternatives.horizon_aware_pricing",
            "priced": {
                "draft_terminal_sd_on_every_horizon": {
                    "partition": "34 / 8",
                    "deployed_v1_n_failed": floor["deployed_v1_finding"][
                        "n_failed"
                    ],
                },
                "settled_sd_on_h1_h2": {
                    "partition": f"{horizon['n_gate_eligible']} / "
                    f"{horizon['n_report_only_tolerance_above_t_max']}",
                    "deployed_v1_n_failed": horizon["deployed_v1_n_failed"],
                    "ols_full_fit_window_n_failed": horizon[
                        "ols_full_fit_window_n_failed"
                    ],
                    "cells_promoted": horizon[
                        "cells_promoted_relative_to_draft"
                    ],
                    "n_tolerances_differing_from_draft": horizon[
                        "n_tolerances_differing_from_draft"
                    ],
                },
            },
            "related": od["horizon_pricing"]["related"],
            "placeholder_in_block": "<RULING 2 horizon_pricing>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "3",
            "name": "age66_female_h1_knife_edge",
            "question": od["age66_female_h1_knife_edge"]["question"],
            "options": {
                "i_keep_as_teeth": {
                    "text": od["age66_female_h1_knife_edge"][
                        "options_as_corrected"
                    ]["i_keep_as_teeth"],
                    "priced": {
                        "tolerance_pp": sweep["age66_female_h1_tolerance_pp"],
                        "windows_with_zero_failures_on_all_34": sweep[
                            "windows_with_zero_failures_on_all_34"
                        ],
                        "best_single_window": sweep[
                            "best_single_window_by_n_failed"
                        ],
                        "windows_clearing_this_cell": sweep[
                            "windows_clearing_age66_female_h1"
                        ],
                    },
                },
                "ii_structural_demotion_as_drafted": {
                    "text": od["age66_female_h1_knife_edge"][
                        "options_as_corrected"
                    ]["ii_structural_demotion_as_drafted"],
                    "status": "UNAVAILABLE AS WRITTEN",
                    "basis": floor["age66_before_fra_transition"],
                },
                "ii_prime_a_different_pre_registered_reason_for_2020": {
                    "text": od["age66_female_h1_knife_edge"][
                        "options_as_corrected"
                    ]["ii_prime_a_different_pre_registered_reason_for_2020"],
                    "status": "none established by any source read",
                },
                "iii_re_price": {
                    "text": od["age66_female_h1_knife_edge"][
                        "options_as_corrected"
                    ]["iii_re_price"],
                    "priced": {
                        grammar: row(grammar, 2.0)[
                            "age66_female_h1_tolerance_pp"
                        ]
                        for grammar in g
                    },
                },
            },
            "consequence_of_demotion": od["age66_female_h1_knife_edge"][
                "consequence_the_packet_did_not_state"
            ],
            "envelopes": {
                "packet_window_grid": {
                    "n_failed": packet_env["n_failed"],
                    "failing_cells": packet_env["failing_cells"],
                    "max_abs_deviation_pp": packet_env["max_abs_deviation_pp"],
                },
                "widened_forecast_class": {
                    "n_failed": widened_env["n_failed"],
                    "max_abs_deviation_pp": widened_env[
                        "max_abs_deviation_pp"
                    ],
                },
            },
            "placeholder_in_block": "<RULING 3 age66_female_h1>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "4",
            "name": "rounding_mode",
            "question": od["rounding_mode"]["question"],
            "priced": {
                "ROUND_HALF_UP": "drafted; reproduces all 42 DRAFT tolerances",
                "ROUND_HALF_EVEN": {
                    "n_cells_differing_from_draft": half_even[
                        "n_cells_differing_from_draft"
                    ],
                    "cells": half_even["result"]["cells_differing_from_draft"],
                    "partition": f"{half_even['result']['n_gate_eligible']} / "
                    f"{half_even['result']['n_report_only_tolerance_above_t_max']}",
                    "deployed_v1_n_failed": half_even["result"][
                        "deployed_v1_n_failed"
                    ],
                },
                "knife_edge_class_to_know_before_any_knob_is_fixed": {
                    "n_cells": knife["n_cells"],
                    "n_gate_eligible": knife["n_gate_eligible"],
                    "cells": sorted(knife["cells"]),
                },
            },
            "placeholder_in_block": "<RULING 4 rounding_mode>",
            "status": "FILED and PRICED; not ruled",
        },
        {
            "id": "5",
            "name": "d0_estimand_construct",
            "question": od["d0_estimand_construct"]["question"],
            "priced": od["d0_estimand_construct"][
                "what_the_artifact_carries_for_each"
            ],
            "what_a_published_choice_forces": od["d0_estimand_construct"][
                "if_published_is_chosen"
            ],
            "placeholder_in_block": "<RULING 5 d0_estimand>",
            "status": "FILED and PRICED; not ruled (everything here is priced on the conditional construct)",
        },
        {
            "id": "6",
            "name": "d1_missing_2021_2022_editions",
            "question": od["d1_missing_2021_2022_editions"]["question"],
            "what_the_pair_already_shows": od["d1_missing_2021_2022_editions"][
                "what_the_pair_already_shows"
            ],
            "priced_interim_alternative": "horizon_pricing (ruling 2)",
            "placeholder_in_block": "<RULING 6 d1_editions>",
            "status": od["d1_missing_2021_2022_editions"]["status"],
        },
        {
            "id": "7",
            "name": "pia_sequencing_constraint",
            "question": (
                "the two live-file 'gate name absent' tests -- "
                "tests/test_claiming_publication_floor.py::"
                "test_no_gate_b2_claiming_exists_in_gates_yaml and "
                "tests/test_pia_rule_coverage.py::"
                "test_no_gate_b2_pia_oracle_exists_in_gates_yaml -- read the "
                "working-tree gates.yaml by design and FAIL the moment "
                "gate_b2_claiming or gate_b2_pia_oracle lands (simulated by "
                "the verification, section 11: exactly those two, nothing "
                "else). The blob-pinned citation itself survives the commit."
            ),
            "constraint": (
                "the lock commit must retire those two assertions (and flip "
                "the pre-lock markers GATE_B2_CLAIMING_BLOCK_LANDED / "
                "GATE_B2_PIA_ORACLE_BLOCK_LANDED) or supersede the floor "
                "artifacts with a v2 in the SAME PR; see flip_plan"
            ),
            "placeholder_in_block": "ceremony_notes.flip_plan",
            "status": "RECORDED as a sequencing constraint; not a threshold ruling",
        },
        {
            "id": "8",
            "name": "e1_clause",
            "question": (
                "the E1 status of every PIA rule rests on the committed "
                "cross-engine artifact runs/pia_cross_engine_v1.json"
            ),
            "clause": (
                "E1 as committed 2026-07-05 at engine ffef7b4 (commit 80d3666), "
                "not re-executed in this ceremony -- for the Axiom half. The "
                "policyengine-us half was re-executed by the verification "
                "(section 16: test_pe_us_simulation_matches_oracle_foundation_"
                "live, 12 foundation cases, checkout a03e82e5, PASSED)."
            ),
            "filed_in": "runs/pia_gate_partition_v1.json (open_questions_for_the_ceremony, S8) and gate_b2_pia_oracle's block",
            "placeholder_in_block": "<RULING S8 e1_clause> (PIA block)",
            "status": "CLAUSE CARRIED; the Axiom half not re-executed by anyone in this ceremony",
        },
    ]


def flip_plan() -> dict[str, Any]:
    return {
        "rule": (
            f"the commit that inserts the {GATE_NAME} block into gates.yaml "
            f"(under `gates:`, a NEW top-level key) flips {MARKER} from "
            "False to True in EVERY file that carries it, IN THE SAME "
            "COMMIT, retires the live-file assertion "
            "tests/test_claiming_publication_floor.py::"
            "test_no_gate_b2_claiming_exists_in_gates_yaml in that commit, "
            "admits the new key at every master-compare site, and changes "
            "nothing else in those files (the gate_m6 / gate_mortality "
            "precedent)"
        ),
        "marker": MARKER,
        "files_carrying_the_marker": [
            "tests/test_gates_derivations.py",
            "tests/test_claiming_gate_floors_v1.py",
        ],
        "live_file_tests_the_flip_retires": [
            "tests/test_claiming_publication_floor.py::"
            "test_no_gate_b2_claiming_exists_in_gates_yaml",
            "tests/test_pia_rule_coverage.py::"
            "test_no_gate_b2_pia_oracle_exists_in_gates_yaml (if the PIA "
            "block lands in the same PR; otherwise its own flip retires it)",
        ],
        "master_compare_sites_that_must_admit_the_new_key": [
            "tests/test_gates_derivations.py::"
            "test_gate_m4_flip_leaves_locked_siblings_byte_identical",
            "tests/test_gate_w1_derivations.py (the `added in (...)` assert)",
            "tests/test_gate_m6_derivations.py (the sole-new-key assert)",
        ],
        "what_flips_with_it": [
            "tests/test_gates_derivations.py: _gate_b2_claiming_block() reads "
            "the LIVE gates.yaml block instead of the artifact's draft "
            "fragment, so every derivation binding runs against the live "
            "contract (LOCKED-HOT, the 2a lesson); the pre-lock guard "
            "inverts to assert the block exists and cites "
            f"{ARTIFACT_REL} with its ratified sha256",
            "gates.yaml: floor_run_sha256 replaces <FILLED AT RATIFICATION> "
            f"with the sha256 of {ARTIFACT_REL} AS RATIFIED; every "
            "<RULING ...> placeholder is replaced by the ratifying round's "
            "text; status -> locked; locked -> true; a history entry is "
            "added",
            "tests/tier_counts.json and tests/README-tiers.md re-refreshed "
            "by LIVE collection",
        ],
    }


# --------------------------------------------------------------------------
# The DRAFT block
# --------------------------------------------------------------------------
def _signed(x: float) -> str:
    return f"{x:+.4f}"


def draft_fragment(
    floor: dict[str, Any],
    draft: dict[str, dict[str, Any]],
    part: dict[str, Any],
    alt: dict[str, Any],
    scan: dict[str, Any],
    finding: dict[str, Any],
    iso: dict[str, Any],
    scope: dict[str, Any],
) -> str:
    """The gate_b2_claiming block as YAML text (2-space indent under
    ``gates:``): the packet's section-5 draft updated to the measured
    bytes and the v2 corrections, every ruling a placeholder."""
    strata = floor["strata"]
    st = strata["conditional_terminal_year"]
    ss = strata["conditional_settled_years"]
    ps = strata["published_settled_years"]
    pt = strata["published_terminal_year"]
    aa = strata["average_age_column"]
    ref = floor["reference_values_pp"]["gate_eligible"]
    gated = part["gate_eligible"]
    report = part["report_only"]
    sd_knob = sd_knob_of(floor)
    g = alt["grammar_and_k_sweep"]["by_grammar"]
    horizon = alt["horizon_aware_pricing"]["result"]
    half_even = alt["rounding_mode_round_half_even"]["result"]
    knife = alt["knife_edge_class"]
    rules = scan["rules"]
    packet_env = scan["envelope_at_the_packet_window_grid"]
    widened_env = scan["post_hoc_best_of_forecast_class_envelope"]
    sweep = scan["ols_window_sweep"]
    transition = floor["age66_before_fra_transition"]
    channels = iso["channels_carrying_the_held_out_actuals"]
    script_channel = channels[-1]
    dne = floor["does_not_establish"]

    def k_row(grammar: str, k: float) -> str:
        r = g[grammar]["by_k"][f"K_{k}"]
        return (
            f"{r['n_gate_eligible']} / "
            f"{r['n_report_only_tolerance_above_t_max']}, deployed fails "
            f"{r['deployed_v1_n_failed']}, OLS-full fails "
            f"{r['ols_full_fit_window_n_failed']}, age66|female|h1 "
            f"{r['age66_female_h1']['tolerance_pp']:.2f}"
        )

    tol_lines = "\n".join(
        f'          "{c}": {draft[c]["tolerance_pp"]:.2f}' for c in gated
    )
    rule_lines = "\n".join(
        f'            "{c}": {{ trend_pp_per_year: {_signed(draft[c]["trend_pp_per_year"])}, '
        f'horizon_years: {draft[c]["horizon_years"]}, rounding: 2, '
        f'unrounded_pp: {draft[c]["unrounded_tolerance_exact"]} }}'
        for c in gated
    )
    ref_lines = "\n".join(f'          "{c}": {ref[c]:.4f}' for c in gated)
    report_lines = "\n".join(
        f'          "{c}": {{ tolerance_pp_would_be: {draft[c]["tolerance_pp"]:.2f}, '
        f'trend_pp_per_year: {_signed(draft[c]["trend_pp_per_year"])}, '
        f"reason: tolerance_above_t_max }}"
        for c in report
    )
    dne_lines = "\n".join(
        "          - >-\n            " + normalized(line) for line in dne
    )
    scope_cells = ", ".join(
        f'"{c}"' for c in scope["out_of_scope_C10"]["cells"]
    )
    failing = ", ".join(f'"{c}"' for c in finding["failing_cells"])
    per_cell_lines = "\n".join(
        f'            "{c}": {{ deviation_pp: {v["deviation_pp"]:.4f}, '
        f'tolerance_pp: {v["tolerance_pp"]:.2f}, margin_pp: {v["margin_pp"]:.4f} }}'
        for c, v in finding["per_failing_cell"].items()
    )
    knife_cells = ", ".join(f'"{c}"' for c in sorted(knife["cells"]))
    promoted = ", ".join(
        f'"{c}"' for c in horizon["cells_promoted_relative_to_draft"]
    )
    clearing = ", ".join(
        str(w) for w in sweep["windows_clearing_age66_female_h1"]
    )
    female_lines = script_channel["line_numbers"]["female"]
    male_lines = script_channel["line_numbers"]["male"]

    text = f"""  gate_b2_claiming:
    # DRAFT -- NOT APPLIED TO gates.yaml. Emitted by
    # scripts/build_claiming_gate_floors_v1.py into
    # runs/claiming_gate_floors_v1.json (draft_gates_yaml_fragment.text) at
    # the threshold-binding sitting of 2026-09-08 (the packet's ceremony
    # step 4). Every number below is machine-derived from the VERIFIED
    # publication floor runs/claiming_publication_floor_v1.json
    # ({SOURCE_FLOOR_COMMITTED[0]:,} B, sha256 {SOURCE_FLOOR_COMMITTED[1][:16]}...) and bound by
    # tests/test_gates_derivations.py (the test_gate_b2_claiming_* bindings,
    # LOCKED-HOT on the gate_m4 pattern); nothing is typed. Ceremony order:
    # floors v1 -> referees A / B -> floors v2 -> verification -> THIS
    # BINDING -> adversarial referee round on these bound thresholds ->
    # verification -> ratifying merge. Every "<RULING ...>" placeholder is an
    # open question the ratifying round must fill; the options and their
    # prices are in the artifact's open_questions_for_the_ceremony. Until
    # then every number is DRAFT and the surface is the drafted grammar's.
    id: b2_claiming_age_distribution
    status: draft_pending_referee_round
    locked: false
    kind: external_reference_temporal_holdout
    derived_from_floor: {SOURCE_FLOOR_REL}
    derived_from_floor_sha256: {SOURCE_FLOOR_COMMITTED[1]}
    derived_from_floor_size_bytes: {SOURCE_FLOOR_COMMITTED[0]}
    floor_run: {ARTIFACT_REL}
    floor_run_sha256: <FILLED AT RATIFICATION>
    covers: >-
      the CLAIMING-AGE module (#74 component CA, Phase B): the CONDITIONAL
      (non-disability-conversion) distribution of retired-worker awardees
      over age at month of entitlement, by sex, as emitted by
      populace_dynamics.claiming.claim_age_pmf. The gate is an EXTERNAL-
      REFERENCE TEMPORAL HOLDOUT: a candidate RULE is fit on SSA Statistical
      Supplement 2023 Table 6.B5.1 entitlement years 1998-2019 and scored on
      the HELD-OUT entitlement years 2020, 2021 and 2022 (horizons h = 1, 2,
      3 from the last fit year), which it has not read. The scored surface
      is EXACTLY the {part['n_gate_eligible']} gate-eligible (category x sex x horizon) cells
      listed in gated_surface; {part['n_report_only']} cells are report-only by the power cap
      (tolerance_above_t_max) and the 6 disability-conversion cells are OUT
      OF SCOPE (routed to the DI surface). No claim-age LEVEL inside the fit
      window is gated (in-window reproduction is a lookup of the file the
      candidate was fit on: gate_w1 round-1 blocker 1, gates.yaml:3758-3761,
      circularity_rule :4359-4365). No benefit LEVEL is gated here; the
      402(q)/(w) factors the module consumes are the oracle's
      (claiming.py:23-28) and belong to gate_b2_pia_oracle. No horizon
      beyond h = 3 is priced. Nothing here certifies the SSA claiming
      PROCESS or any multi-cohort reading of an entitlement year.
    holdout_basis: [ssa_supplement_2023_6b5_1_entitlement_years_2020_2022]
    fit_basis: [ssa_supplement_2023_6b5_1_entitlement_years_1998_2019]
    data_staged: >-
      Both editions are committed IN-REPO and sha-pinned:
      data/external/ssa_claim_ages_2023supplement.json (schema
      ssa_claim_ages.v1, 1998-2022, 50 rows; sha256
      {floor['sources']['edition_2023']['sha256'][:16]}...) and
      data/external/ssa_claim_ages_2014supplement.json (1998-2013, 32 rows;
      sha256 {floor['sources']['edition_2014']['sha256'][:16]}...). The 2014 edition is the
      REVISION-FLOOR basis, not a scoring basis. The publication floor
      {SOURCE_FLOOR_REL} EXISTS (floors v2 at cd8f167,
      independently verified) and the gate-schema artifact
      {ARTIFACT_REL} derives this block from it. The 2021 and
      2022 editions are NOT staged (<RULING 6 d1_editions>).
    lock_ceremony:
      exists: false
      required: >-
        The SAME ceremony gate-2a / 2b / 2c / M4 / W1 / mortality follow:
        floor -> adversarial referees -> fixes -> verification -> THRESHOLD
        BINDING (this block) -> adversarial referee round on the bound
        thresholds -> fixes -> verification -> ratifying merge, which fills
        every placeholder, sets floor_run_sha256, flips
        GATE_B2_CLAIMING_BLOCK_LANDED and retires the live-file guard test
        in the same commit. NOT YET RUN past the binding.
    thresholds:
      locked: false
      status: draft_pending_referee_round
      tranche_id: b2_claiming_age_distribution
      kind: external_reference_temporal_holdout
      reference_run: data/external/ssa_claim_ages_2023supplement.json
      reference_run_sha256: {floor['sources']['edition_2023']['sha256']}
      floor_run: {ARTIFACT_REL}
      floor_run_sha256: <FILLED AT RATIFICATION>
      derived_from:
        path: {SOURCE_FLOOR_REL}
        sha256: {SOURCE_FLOOR_COMMITTED[1]}
        size_bytes: {SOURCE_FLOOR_COMMITTED[0]}
        blocks: ["strata.conditional_terminal_year.sd_pp", "strata.conditional_settled_years.sd_pp",
          "power_cap.derivations[*].trend_pp_per_year", "reference_values_pp"]
      superseded_evidence: >-
        runs/claiming_reference_v1.json (sha256
        {floor['sources']['claiming_reference_v1']['sha256'][:16]}...) -- the reported-not-gated held-out
        computation on the PUBLISHED 8-category construct (nearest-year max
        3.2 pp; linear-trend max 8.1623). It is the ROUND-0 record, retained
        committed and reproduced by the floor
        (reproduces_claiming_reference_v1.all_match true); this DRAFT scores
        the CONDITIONAL 7-category construct the module emits
        (<RULING 5 d0_estimand>).
      estimand: >-
        For each (sex, entitlement year in 2020-2022) the CONDITIONAL
        claim-age share vector over the seven published non-conversion
        categories {{age62, age63, age64, age65, age66, age67_69, age70plus}},
        renormalised to sum to 100 -- exactly the object claim_age_pmf
        returns (claiming.py:262-303) re-aggregated to the reference's own
        category partition. The uniform age67_69 -> {{67, 68, 69}} split
        (claiming.py:92-99) is INERT under that re-aggregation and is
        neither gated nor credited. Per the standing rule
        description_claims_exactly_the_scored_surface (gates.yaml:1056,
        :3294, :4869) the surface claimed is EXACTLY the gated cells: NOT the
        SSA claiming process, NOT any benefit level, NOT the disability-
        conversion flow, and NOT the multi-cohort composition of an
        entitlement year (expected_reduction_factor is a documented
        SINGLE-COHORT reading, claiming.py:396-405, not certified here).
      statistic: >-
        Per gated cell, the absolute deviation in published percentage
        points |predicted_pp - reference_pp| on the 0-100 conditional-share
        scale, the prediction UNROUNDED (deviation_arithmetic in the floor:
        the rounded-prediction path differs by at most one 4-dp ulp and
        flips no verdict under either rule scored both ways). Bounded and
        unit-honest; NEVER |ln ratio| -- a share can be 0.
      protocol:
        option: >-
          external-reference temporal holdout. The candidate is a RULE
          mapping (sex, entitlement year) to a conditional share vector, fit
          on 1998-2019 ONLY, evaluated at 2020, 2021 and 2022.
        deterministic: true
        seeds: none
        seed_rule_not_applicable: >-
          There is no simulation draw and no person split, so no seed
          conjunction and no 4-of-5 rule. A candidate that additionally
          SAMPLES integer ages (draw_claim_ages, claiming.py:306-332) does
          not enter this gate: the sampler is claim_age_pmf plus multinomial
          noise, so gating the PMF gates the sampler's estimand.
        fit_isolation:
          required: true
          rule: >-
            The candidate MUST be constructed against a reference object
            PHYSICALLY restricted to entitlement years 1998-2019. Passing
            the full document and promising not to look is NOT acceptable:
            the loader caches the whole file (claiming.py:169-179) and the
            in-range path returns the held-out row exactly (:200-213, :230).
            A run whose candidate had access to a 2020-2022 row is
            INVALIDATED and must be re-registered.
          channels_carrying_the_held_out_actuals: >-
            the 2023 edition and EVERY committed copy of its 2020-2022 rows:
            data/external/ssa_claim_ages_2023supplement.json (the reference
            document), scripts/build_ssa_claim_ages.py (its verbatim
            transcription, RAW_TABLE lines {male_lines[0]}-{male_lines[-1]} male and
            {female_lines[0]}-{female_lines[-1]} female -- verifier F-A), runs/claiming_reference_v1.json
            (published-construct actuals), runs/claiming_publication_floor_v1.json
            (reference_values_pp, holdout_rules.per_cell.*.*.actual, every
            tolerance and every candidate score) and
            runs/claiming_gate_floors_v1.json (this block's own artifact).
            Physical isolation from public data is impossible; the defence
            is procedural -- rule class and fit window registered on issue
            #42 with a justification independent of these artifacts, before
            any scoring, one shot, no_self_rescue.
        circularity_disclosure: >-
          gate_w1's round-1 blocker 1 (gates.yaml:3758-3761) was that the
          deployed module samples from the anchor it is scored against; the
          ratified circularity_rule (:4359-4365) keeps the 14 non-conversion
          claim-age cells report-only (:4568-4573). This gate escapes it
          only because a candidate fit on 1998-2019 has NEVER READ the
          2020-2022 rows it is scored on; in-window reproduction stays
          REPORT-ONLY because it is a lookup of the fit file; and the
          residual circularity -- every held-out actual and every tolerance
          is published in the channels named above -- is disclosed rather
          than denied. The frontier scan in degenerate_candidates is post
          hoc; once a scanned rule is registered its scores are prior
          knowledge.
        pass_rule: >-
          CONJUNCTION over the {part['n_gate_eligible']} gate-eligible cells: the candidate passes
          iff every gated cell's |predicted_pp - reference_pp| <= that cell's
          tolerance_pp. Report-only cells and the out-of-scope conversion
          cells publish on their own rules and never gate. No seed slack.
      power_cap:
        t_max_pp: {T_MAX_PP}
        source: >-
          inherited VERBATIM from the ratified gate_w1 family-B knob
          (gates.yaml:4366-4368, t_max_pp 3.0), the only locked precedent in
          this file for an anchor tolerance denominated in percentage points.
        rule: >-
          a cell is gate-eligible iff its derived tolerance_pp <= T_max_pp.
          Which cells demote is DERIVED from the trend term, never
          hand-picked: the fast-moving age62 and age66 series exceed the cap
          at horizons 2-3.
        demoted_and_report_only: >-
          {part['n_report_only']} cells, ALL by the machine reason tolerance_above_t_max.
          Separately, 6 disability-conversion cells are excluded by SCOPE
          before any candidate runs (report_only.out_of_module_scope).
        revision_grammar: "<RULING 1 grammar_and_k_rev>"
        revision_grammar_drafted: >-
          K_REV * sd(|revision|) on the conditional terminal-year stratum
          (K_REV {K_REV}, sd knob {sd_knob} pp = the 4-dp rounding of {st['sd_pp']}). This
          follows NEITHER house grammar (gate-1 derives round(mean + k * sd,
          r); gate_w1 family B multiplies the sd of a zero-mean residual,
          whose analogue here is the SIGNED revision, sd {st['sd_signed_pp']}). Priced
          beside it, from the same floor bytes (artifact alternatives.
          grammar_and_k_sweep): drafted K 1.5 / 2.0 / 2.5 -> {k_row('k_times_sd_abs_DRAFT', 1.5)};
          {k_row('k_times_sd_abs_DRAFT', 2.0)}; {k_row('k_times_sd_abs_DRAFT', 2.5)}.
          mean + K sd(|d|) K 2.0 -> {k_row('mean_plus_k_times_sd_abs', 2.0)}.
          K sd(signed d) K 2.0 -> {k_row('k_times_sd_signed', 2.0)}.
          max |d| (d2) -> {k_row('max_abs_revision_d2', 2.0)}.
        horizon_pricing: "<RULING 2 horizon_pricing>"
        horizon_pricing_drafted: >-
          the terminal-year sd on EVERY horizon (conservative: h1 = 2020 is
          three years settled and h2 = 2021 two years settled in the 2023
          edition; the pair shows rows one to three years settled moved
          0.0). Priced beside it (alternatives.horizon_aware_pricing):
          settled sd {round(ss['sd_pp'], 4)} on h1 / h2 -> {horizon['n_gate_eligible']} / {horizon['n_report_only_tolerance_above_t_max']}, deployed fails
          {horizon['deployed_v1_n_failed']}, OLS-full fails {horizon['ols_full_fit_window_n_failed']}, promoted {promoted},
          {horizon['n_tolerances_differing_from_draft']} gated tolerances differ from the DRAFT.
        rounding_mode: "<RULING 4 rounding_mode>"
        rounding_mode_drafted: >-
          ROUND_HALF_UP in Decimal on the exact sum of the three summands,
          quantised to 2 decimals. ROUND_HALF_EVEN differs on exactly
          {len(half_even['cells_differing_from_draft'])} cell ({', '.join(half_even['cells_differing_from_draft'])}: unrounded {draft[TIE_CELL]['unrounded_tolerance_exact']}
          -> {draft[TIE_CELL]['tolerance_pp']:.2f} half-up / {draft[TIE_CELL]['tolerance_pp_round_half_even']:.2f} half-even) and nowhere else; the
          partition is {half_even['n_gate_eligible']} / {half_even['n_report_only_tolerance_above_t_max']} under both. The knife-edge class
          (unrounded tolerance within {knife['band_pp']} pp of a 2-decimal boundary) has
          {knife['n_cells']} cells, {knife['n_gate_eligible']} gate-eligible: {knife_cells}.
          The v1 float evaluation reproduces every DRAFT tolerance
          (power_cap.rounding_mode.float_path_reproduces_every_tolerance).
        sd_knob_rounding_check: >-
          the 4-dp sd knob vs the full-precision sd moves exactly one
          2-decimal tolerance (the tie cell, 1.53 -> 1.52) and no
          gate-eligibility flag (floor power_cap.sd_knob_rounding_check).
      floor:
        # THE FLOOR IS A PUBLICATION FLOOR, NOT A SAMPLING FLOOR. Table 6.B5.1
        # is Master Beneficiary Record 100 percent data, not a sample, so no
        # half-split null exists and the gate-1 / 2 / m4 construction does not
        # apply. The measurable noise is REVISION + ROUNDING.
        construction: >-
          cross-EDITION revision of the same table: the committed 2014
          edition (entitlement years 1998-2013) against the committed 2023
          edition, on the 1998-2013 overlap, in conditional-share space. SSA
          states the mechanism (verbatim in both editions): "{floor['no_sampling_floor']['retroactive_revision_sentence']}"
        measured_by: {SOURCE_FLOOR_REL} (floors v2, cd8f167; verified)
        strata:
          conditional_settled_years:  {{ years: '1998-2012', n_cells: {ss['n_cells']}, nonzero_cells: {ss['nonzero_cells']}, mean_pp: {ss['mean_pp']}, sd_pp: {ss['sd_pp']}, max_pp: {ss['max_pp']} }}
          conditional_terminal_year:  {{ years: '2013', n_cells: {st['n_cells']}, nonzero_cells: {st['nonzero_cells']}, mean_pp: {st['mean_pp']}, sd_pp: {st['sd_pp']}, sd_signed_pp: {st['sd_signed_pp']}, max_pp: {st['max_pp']} }}
          published_settled_years:    {{ years: '1998-2012', n_cells: {ps['n_cells']}, nonzero_cells: {ps['nonzero_cells']}, mean_pp: {ps['mean_pp']}, sd_pp: {ps['sd_pp']}, max_pp: {ps['max_pp']} }}
          published_terminal_year:    {{ years: '2013', n_cells: {pt['n_cells']}, nonzero_cells: {pt['nonzero_cells']}, mean_pp: {pt['mean_pp']}, sd_pp: {pt['sd_pp']}, max_pp: {pt['max_pp']} }}
          average_age_column:         {{ years: '1998-2013', n_rows: {aa['n_rows']}, nonzero_rows: {aa['nonzero_rows']}, max_years: {aa['max_years']} }}
        strata_note: >-
          conditional_settled_years.nonzero_cells is {ss['nonzero_cells']}, not the packet's 1
          (packet correction 1: one published cell moving renormalises its
          whole row); the conditional strata's signed revisions sum to zero
          by construction, so sd_signed_pp equals the RMS.
        applicable_stratum: conditional_terminal_year
        applicable_stratum_rationale: >-
          2022 IS the terminal year of the 2023 edition, the single year most
          exposed to retroactive revision; 2020-2021 were terminal in the
          2021 / 2022 editions, which are NOT staged. Pricing all three
          horizons on the terminal stratum is the CONSERVATIVE choice and is
          priced as such (<RULING 2 horizon_pricing>, <RULING 6 d1_editions>).
        finding: >-
          Publication revision is ENTIRELY a terminal-year effect. All {pt['nonzero_cells']}
          published terminal-year cells moved (max {pt['max_pp']} pp); across the fifteen
          settled years exactly ONE published cell of {ps['n_cells']} moved, by a single
          0.1 pp rounding tick (age67_69|male|2008); the average_age column
          did not move at all. The award-count column revised in settled
          years too (below share resolution) and by several percent in the
          terminal year (floor number_thousands_column).
        does_not_establish:
{dne_lines}
      gated_surface:
        # GATED cells ({part['n_gate_eligible']}). tolerance_pp == quantize(K_REV * sd_knob
        # + |trend_pp_per_year| * horizon_years + ROUNDING_PP, 2 dp, ROUND_HALF_UP)
        # in Decimal; K_REV {K_REV}, sd_knob {sd_knob}, ROUNDING_PP {ROUNDING_PP}; gate-eligible
        # iff <= T_max_pp {T_MAX_PP}. Every value is recomputed from the floor's
        # strata and trends by tests/test_gates_derivations.py.
        tolerances_pp:
{tol_lines}
        derivations:
          floor_run: {SOURCE_FLOOR_REL}
          floor_key: strata.conditional_terminal_year.sd_pp
          rule: >-
            quantize(K_REV * revision_sd_terminal_pp + abs(trend_pp_per_year) *
            horizon_years + ROUNDING_PP, 2, ROUND_HALF_UP)
          knobs: {{k_rev: {K_REV}, revision_sd_terminal_pp: {sd_knob}, rounding_pp: {ROUNDING_PP},
            t_max_pp: {T_MAX_PP}, fit_window: [1998, 2019], horizon_years: [1, 2, 3],
            rounding_mode: ROUND_HALF_UP}}
          trend_estimator: closed-form OLS slope of the conditional share on 1998-2019, rounded to 4 decimals
          binding_tests: [test_gate_b2_claiming_tolerances_bind_to_floor_strata_and_trends,
            test_gate_b2_claiming_partition_34_8_recomputes,
            test_gate_b2_claiming_grammar_and_k_perturbation_fails_on_any_knob_change,
            test_gate_b2_claiming_k_by_rounding_sweep_recomputes,
            test_gate_b2_claiming_horizon_aware_pricing_recomputes,
            test_gate_b2_claiming_rounding_mode_tie_and_knife_edge_class,
            test_gate_b2_claiming_failure_sets_recompute_from_the_edition,
            test_gate_b2_claiming_frontier_scan_recomputes,
            test_gate_b2_claiming_mutated_builder_fails_the_binding]
          rules:
{rule_lines}
        reference_values_pp:  # the held-out conditional shares (4 dp) the cells score against
{ref_lines}
        # REPORT-ONLY by tolerance_above_t_max ({part['n_report_only']} cells).
        report_only_tolerance_above_t_max:
{report_lines}
      report_only:
        out_of_module_scope:
          # 6 cells excluded BEFORE any candidate runs, by SCOPE, not by
          # power and not by any candidate's performance: (a) the module
          # excludes conversions from its emitted PMF by design
          # (claiming.py:16-18, :244-256, :296-303) -- a conversion is an
          # auto-conversion at FRA, not a claiming choice; (b) gates.yaml
          # :4388-4392 assigns the conversion share to the deployed M4
          # disability dynamics, "NOT read from 6.B5.1".
          cells: [{scope_cells}]
          reason: {OUT_OF_SCOPE_REASON}
          published: >-
            the conversion share IS published with every candidate run
            (conversion_share, claiming.py:244-256) and is reconciled
            against the gate_w1 family-B retained anchor
            (claim_age.disability_conversion|{{female,male}}, gates.yaml
            :4467-4487) -- reported, never gated here.
        published_8_category_construct: >-
          the published (un-renormalised) 8-category deviations are
          published alongside every run so runs/claiming_reference_v1.json
          stays comparable across the construct change. Reported, never
          gated.
        in_window_reproduction: >-
          exact reproduction of entitlement years 1998-2019 is REPORTED as
          an integrity check and NEVER gated (circularity_disclosure).
      degenerate_candidates:
        # Teeth and the faithful_candidate_oc SUBSTITUTE (C7): a deterministic
        # rule has no seed and no operating characteristic, so the frontier of
        # a scanned rule class stands in. RECOMPUTED by the gate artifact from
        # the floor's scoring frame and equal to the floor's scan; a scan, not
        # a proof that no admissible rule does better.
        deployed_v1_nearest_year:
          description: the module's documented default (claiming.py:200-213), predict every held-out year with 2019
          gated_cells_failed: {finding['n_failed']}
          failing_cells: [{failing}]
          max_pp: {finding['max_abs_deviation_pp']}
          mean_pp: {finding['mean_abs_deviation_pp']}
          per_failing_cell:
{per_cell_lines}
          verdict: >-
            FAILS {finding['n_failed']} of {finding['n_gate_eligible_cells']} (C8). Stated up front: adopting this gate as drafted
            means the CURRENTLY DEPLOYED claiming rule does not pass it. Under
            both house grammars at K 2.0 the same rule fails 4; under
            horizon-aware pricing 15. Whether that is bite or mis-pricing is
            the round's C8, priced in alternatives.
        uniform_over_seven_categories:
          gated_cells_failed: {rules['uniform_over_seven_categories']['n_failed']}
          max_pp: {rules['uniform_over_seven_categories']['max_abs_deviation_pp']}
          verdict: the surface rejects a shapeless candidate.
        fit_window_mean:
          gated_cells_failed: {rules['fit_window_mean']['n_failed']}
          max_pp: {rules['fit_window_mean']['max_abs_deviation_pp']}
          verdict: the surface rejects a level-only candidate.
        sex_pooled_nearest_year:
          gated_cells_failed: {rules['sex_pooled_nearest_year']['n_failed']}
          max_pp: {rules['sex_pooled_nearest_year']['max_abs_deviation_pp']}
          verdict: the SEX dimension has independent bite.
        best_named_rules:
          ols_last_5: {{ gated_cells_failed: {rules['ols_last_5']['n_failed']}, max_pp: {rules['ols_last_5']['max_abs_deviation_pp']}, mean_pp_4dp_convention: {rules['ols_last_5']['mean_abs_deviation_pp_4dp_rounded_convention']} }}
          damped_local_trend_w5_d1.0: {{ gated_cells_failed: {rules['damped_local_trend_w5_d1.0']['n_failed']}, max_pp: {rules['damped_local_trend_w5_d1.0']['max_abs_deviation_pp']} }}
          ols_last_6_from_the_window_sweep: {{ gated_cells_failed: {sweep['rows']['ols_last_6']['n_failed']} }}
        ols_window_sweep: >-
          every OLS window 2..22 scored: no single window clears all {part['n_gate_eligible']}
          cells; windows {clearing} clear age66|female|h1 (OLS-13 at
          {sweep['rows']['ols_last_13']['age66_female_h1_deviation_pp']} against {sweep['age66_female_h1_tolerance_pp']}); the packet's grid {{3, 5, 10, 22}} clears none.
        post_hoc_envelopes:
          packet_window_grid_8_rules: {{ gated_cells_failed: {packet_env['n_failed']}, failing_cells: [{', '.join(f'"{c}"' for c in packet_env['failing_cells'])}], max_pp: {packet_env['max_abs_deviation_pp']}, mean_pp: {packet_env['mean_abs_deviation_pp']} }}
          widened_forecast_class_{widened_env['n_rules']}_rules: {{ gated_cells_failed: {widened_env['n_failed']}, max_pp: {widened_env['max_abs_deviation_pp']}, mean_pp: {widened_env['mean_abs_deviation_pp']}, argmax_cell: "{widened_env['argmax_cell']}" }}
          note: NOT prospectively achievable (best rule per cell after the fact); bounds the frontier of THIS enumeration only.
        catch_structure: >-
          shapeless and level-only candidates fail broadly; sex-blind
          candidates fail {rules['sex_pooled_nearest_year']['n_failed']} cells; the deployed frozen-year rule fails the
          two fastest-drifting families (age62 at h1, age70plus at h2 / h3)
          and the 2020 age66 level shift, whose cause is UNDETERMINED
          (packet correction 7: the age66_before_fra composition break
          begins in entitlement year {transition['first_populated_year']['female']} and does not cover h1 = 2020).
          Every gated cell is failed by at least one scanned rule.
      knife_edge:
        cell: "{KNIFE_CELL}"
        ruling: "<RULING 3 age66_female_h1>"
        options_as_corrected: >-
          (i) keep as teeth at the drafted {draft[KNIFE_CELL]['tolerance_pp']:.2f} pp (no single window clears
          all {part['n_gate_eligible']}; the best single windows fail exactly this cell);
          (ii) structural demotion AS DRAFTED is UNAVAILABLE AS WRITTEN --
          the 2021 age66_before_fra break (null through 2020; female
          {transition['values_by_sex_and_year']['female']['2021']} / male {transition['values_by_sex_and_year']['male']['2021']} in 2021) does not cover entitlement year 2020
          (packet correction 7); (ii') a different pre-registered reason for
          2020 -- none is established by any source read; (iii) re-price --
          about 2.9 pp under either house grammar at K 2.0 (mean + K sd
          {g['mean_plus_k_times_sd_abs']['by_k']['K_2.0']['age66_female_h1']['tolerance_pp']:.2f}, K sd(signed) {g['k_times_sd_signed']['by_k']['K_2.0']['age66_female_h1']['tolerance_pp']:.2f}), where OLS-full ({sweep['rows']['ols_last_22']['age66_female_h1_deviation_pp']}) clears
          and the deployed rule ({finding['per_failing_cell'][KNIFE_CELL]['deviation_pp']}) does not. Consequence to weigh:
          demoting the cell takes the packet-grid envelope from {packet_env['n_failed']} failure to 0.
          Whatever is ruled must be adopted BEFORE any candidate runs
          (no_self_rescue).
      governance:
        registration: >-
          Pre-registered on issue #42, as every gate-1 / gate-2 / m4 / w1
          candidate run. A gate_b2_claiming candidate registers its rule
          class, its fit window, its fit-isolation mechanism and its
          predicted vectors BEFORE scoring. Outer runs are one-shot.
        amendment_rules:
          inherits: gate_1
          no_self_rescue: >-
            Inherited verbatim from gate_1.amendment_rules (gates.yaml
            :565-568): no candidate's committed run verdict changes under a
            rule proposed after that run. Sharpened for this gate: a cell may
            NOT be demoted because a candidate failed it. The only admissible
            demotion reasons are the DERIVED power cap
            (tolerance_above_t_max) and the candidate-independent SCOPE
            reason above, both fixed at lock.
          amendments_only_via: >-
            public proposal + adversarial referee round + verification +
            maintainer ratification by merge.
          description_claims_exactly_the_scored_surface: >-
            Bound by the standing rule (gates.yaml:1056, :3294, :4869):
            covers / holdout_basis / estimand claim EXACTLY the {part['n_gate_eligible']} gated
            cells. No claiming behaviour outside entitlement years
            2020-2022, no horizon beyond h = 3, no benefit level, no
            disability-conversion flow and no multi-cohort reading is
            headlined beyond what the cells gate.
        candidate_scale: >-
          PINNED to the full published margin: 6.B5.1 is Master Beneficiary
          Record 100 percent data, so there is no subsample and no scale to
          fix. This is why the floor is a publication floor.
        weight_definition: >-
          NONE. The scored quantities are SSA's own published percentage
          distributions; no reweighting is applied by the candidate or the
          scorer. Any candidate that reweights the reference is INVALIDATED.
      certification_scope:
        tranche: b2_claiming_age_distribution
        horizon: >-
          h in {{1, 2, 3}} from the last fit year 2019 = entitlement years
          2020, 2021, 2022 (C11). gate_w1 deploys at anchor_frame_year 2024
          with claim_age_delta_years 2 (gates.yaml:4366-4368), h = 2 and
          growing; a 2030+ frame is outside anything this gate prices.
        certifies: >-
          that a candidate claiming rule reproduces the conditional
          claim-age distribution of retired-worker awardees, by sex, on
          three Supplement entitlement years it has not read, at horizons
          1-3 years past its fit window, on exactly the gated cells, within
          a publication-revision-priced tolerance. Nothing else (C13).
        supports:
          - >-
            the #74 CA (claiming) component for the claiming /
            mortality-dependent provision class on the OBSERVED frame, at
            h <= 3.
          - >-
            an ARGUMENT for de-circularising gate_w1 family B's 14
            report-only claim-age cells (gates.yaml:4568-4573): a candidate
            certified on a temporal holdout is no longer "the module that
            samples from the anchor it is scored against". Re-gating those
            cells still requires a gate_w1 amendment with its own ceremony;
            this gate makes it arguable and does not make it (C14).
        does_not_support:
          - >-
            any benefit LEVEL: the 402(q)/(w) factors the module multiplies
            through (claiming.py:360-376) are the oracle's and belong to
            gate_b2_pia_oracle.
          - >-
            extrapolation beyond h = 3.
          - >-
            the disability-conversion flow (out of scope above) or the
            multi-cohort composition of an entitlement year: the module's
            expected_reduction_factor is documented as a SINGLE-COHORT
            reading (claiming.py:396-405); nothing here certifies it.
          - >-
            the SSA claiming PROCESS: the estimand is a published share
            vector, not behaviour.
      open_rulings:
        # Each is FILED and PRICED in runs/claiming_gate_floors_v1.json
        # open_questions_for_the_ceremony; none is made here.
        "1": "<RULING 1 grammar_and_k_rev> -- power_cap.revision_grammar"
        "2": "<RULING 2 horizon_pricing> -- power_cap.horizon_pricing"
        "3": "<RULING 3 age66_female_h1> -- knife_edge.ruling"
        "4": "<RULING 4 rounding_mode> -- power_cap.rounding_mode"
        "5": "<RULING 5 d0_estimand> -- conditional (drafted) vs published; a published choice forces a v2 floor with an eight-category cap and the six conversion cells re-entering"
        "6": "<RULING 6 d1_editions> -- stage the 2021 / 2022 editions or accept horizon_pricing as the interim"
        "7": "sequencing constraint -- ceremony_notes.flip_plan (the two live-file guard tests)"
        "8": "<RULING S8 e1_clause> -- carried in gate_b2_pia_oracle; E1 as committed 2026-07-05 at engine ffef7b4, not re-executed"
      ceremony_notes:
        placeholders_the_ratifying_round_must_fill:
          - "<RULING 1 grammar_and_k_rev>"
          - "<RULING 2 horizon_pricing>"
          - "<RULING 3 age66_female_h1>"
          - "<RULING 4 rounding_mode>"
          - "<RULING 5 d0_estimand>"
          - "<RULING 6 d1_editions>"
          - "<FILLED AT RATIFICATION>"
        flip_plan: >-
          the commit that inserts this block flips
          GATE_B2_CLAIMING_BLOCK_LANDED from False to True in
          tests/test_gates_derivations.py and
          tests/test_claiming_gate_floors_v1.py, RETIRES
          tests/test_claiming_publication_floor.py::
          test_no_gate_b2_claiming_exists_in_gates_yaml (and its PIA twin
          tests/test_pia_rule_coverage.py::
          test_no_gate_b2_pia_oracle_exists_in_gates_yaml if
          gate_b2_pia_oracle lands in the same PR) -- both read the live
          file by design and fail the moment the block lands -- admits
          the new key at the three master-compare sites
          (test_gate_m4_flip_leaves_locked_siblings_byte_identical,
          tests/test_gate_w1_derivations.py, tests/test_gate_m6_derivations.py),
          fills floor_run_sha256 with the ratified sha256 of
          runs/claiming_gate_floors_v1.json, and re-refreshes the tier
          manifest -- all in the SAME commit.
        derivations_bound_by: tests/test_gates_derivations.py (test_gate_b2_claiming_*) and tests/test_claiming_gate_floors_v1.py
        wording_audit: >-
          the two words the standing wording audit forbids occur 0 times in
          this block (artifact wording_audit.forbidden_word_counts); the
          circularity disclosure present; the standing rule cited; every
          does_not_establish line of the floor carried under floor.
"""
    return text


# --------------------------------------------------------------------------
# Wording audit (C13, the standing rule, the floor's does_not_establish)
# --------------------------------------------------------------------------
def required_phrases(floor: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        {
            "item": "the standing rule (C13)",
            "required_phrases": [
                "description_claims_exactly_the_scored_surface",
                "gates.yaml:1056, :3294, :4869",
            ],
        },
        {
            "item": "circularity disclosure (C3)",
            "required_phrases": ["circularity_disclosure", "NEVER READ"],
        },
        {
            "item": "no claiming behaviour outside 2020-2022",
            "required_phrases": [
                "No claiming behaviour outside entitlement years 2020-2022"
            ],
        },
        {
            "item": "no benefit level",
            "required_phrases": ["No benefit LEVEL is gated here"],
        },
        {
            "item": "no conversion flow",
            "required_phrases": ["OUT OF SCOPE", OUT_OF_SCOPE_REASON],
        },
        {
            "item": "no multi-cohort reading (claiming.py:396-405)",
            "required_phrases": ["SINGLE-COHORT", "claiming.py:396-405"],
        },
        {
            "item": "the horizon stated (C11)",
            "required_phrases": [
                "h in {1, 2, 3}",
                "extrapolation beyond h = 3",
            ],
        },
        {
            "item": "what a pass authorises (C14)",
            "required_phrases": ["does not make it (C14)"],
        },
        {
            "item": "fit isolation names every channel (F-A)",
            "required_phrases": [
                "EVERY committed copy of its 2020-2022 rows",
                "scripts/build_ssa_claim_ages.py",
            ],
        },
    ]
    for i, line in enumerate(floor["does_not_establish"]):
        items.append(
            {
                "item": f"floor does_not_establish[{i}] carried",
                "required_phrases": [normalized(line)],
            }
        )
    return items


def wording_audit(
    fragment: str, artifact_json_without_audit: str, floor: dict[str, Any]
) -> dict[str, Any]:
    flat = normalized(fragment)
    low_f = flat.lower()
    low_a = normalized(artifact_json_without_audit).lower()
    forbidden = {
        w: {
            "fragment": len(re.findall(rf"\b{w}\b", low_f)),
            "artifact_excluding_this_block": len(
                re.findall(rf"\b{w}\b", low_a)
            ),
        }
        for w in FORBIDDEN_WORDS
    }
    checklist = []
    for item in required_phrases(floor):
        present = {p: (p in flat) for p in item["required_phrases"]}
        checklist.append(
            {
                **item,
                "required_present": present,
                "holds": all(present.values()),
            }
        )
    return {
        "scope": (
            "the draft gate_b2_claiming block (draft_gates_yaml_fragment."
            "text) and this artifact's JSON with this audit block removed. "
            "No PR is opened by this sitting; the PR body's audit with the "
            "same word list is owed by the verification round at PR time."
        ),
        "forbidden_words": list(FORBIDDEN_WORDS),
        "forbidden_word_counts": forbidden,
        "forbidden_words_absent_from_fragment": all(
            v["fragment"] == 0 for v in forbidden.values()
        ),
        "forbidden_words_absent_from_artifact": all(
            v["artifact_excluding_this_block"] == 0 for v in forbidden.values()
        ),
        "circularity_disclosure_present": "circularity_disclosure" in fragment,
        "required_phrases": checklist,
        "all_required_phrases_present": all(c["holds"] for c in checklist),
    }


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def run(verbose: bool = True) -> dict[str, Any]:
    started = time.time()
    floor = load_source_floor()
    edition = load_edition(floor)
    frame = scoring_frame(edition)

    draft = derive_tolerances(floor)
    check_against_committed(draft, floor)
    part = partition_of(draft)
    gated = part["gate_eligible_tolerances_pp"]
    # cross-check the derivation against the floor builder's own arithmetic
    for cell in cell_order():
        _, _, h = split_cell(cell)
        if (
            fb._tolerance(
                sd_knob_of(floor), draft[cell]["trend_pp_per_year"], h
            )
            != draft[cell]["tolerance_pp"]
        ):
            raise RuntimeError(f"{cell}: floor builder arithmetic disagrees")
    if verbose:
        print(
            f"derived {len(draft)} tolerances: {part['n_gate_eligible']} gated / "
            f"{part['n_report_only']} report-only; equal to the floor's DRAFT surface"
        )

    alt = alternatives(floor, frame, draft)
    scan = frontier_scan(floor, frame, gated)
    finding = deployed_finding(floor, frame, gated)
    iso = fit_isolation(floor, edition)
    scope = certification_scope(floor, part)
    citations = gates_yaml_citations()
    if verbose:
        print(
            "alternatives cross-checked against the floor: "
            f"{len(K_GRID) * 4} grammar x K rows, "
            f"{len(K_SWEEP) * len(ROUNDING_SWEEP)} K x rounding rows, "
            "horizon-aware, half-even; frontier scan and deployed finding equal"
        )
        print(
            f"fit isolation: {iso['n_channels']} channels; scan hit "
            f"{iso['scan']['files_hit']} ({iso['scan']['n_files_scanned']} files)"
        )

    fragment = draft_fragment(
        floor, draft, part, alt, scan, finding, iso, scope
    )
    parsed = yaml.safe_load("gates:\n" + fragment)["gates"][GATE_NAME]
    if parsed["status"] != "draft_pending_referee_round" or parsed["locked"]:
        raise RuntimeError("the draft block must parse as a draft")
    if (
        len(parsed["thresholds"]["gated_surface"]["tolerances_pp"])
        != part["n_gate_eligible"]
    ):
        raise RuntimeError("the draft block's gated surface is short")
    fragment_meta = {
        "text": fragment,
        "text_sha256": _sha_of_text(fragment),
        "n_lines": len(fragment.splitlines()),
        "n_bytes": len(fragment.encode("utf-8")),
        "indent": (
            "2 spaces under `gates:`; parse with "
            f"yaml.safe_load('gates:\\n' + text)['gates']['{GATE_NAME}']"
        ),
        "status_in_text": "draft_pending_referee_round",
        "written_nowhere_else": (
            "asserted by tests/test_claiming_gate_floors_v1.py and "
            "tests/test_gates_derivations.py: gates.yaml mentions neither "
            f"{GATE_NAME} nor this artifact nor {SOURCE_FLOOR_REL} while "
            f"{MARKER} is False, and the text occurs in no other tracked file"
        ),
    }

    gate_partition = {
        "gate_eligible": part["gate_eligible"],
        "report_only": part["report_only"],
        "n_gate_eligible": part["n_gate_eligible"],
        "n_report_only": part["n_report_only"],
        "report_only_reasons": {
            c: {
                "reason": "tolerance_above_t_max",
                "tolerance_pp_would_be": draft[c]["tolerance_pp"],
            }
            for c in part["report_only"]
        },
        "out_of_module_scope": floor["power_cap"]["out_of_module_scope"],
        "eligibility_rule_applied": (
            f"tolerance_pp <= t_max_pp {T_MAX_PP} under the DRAFT grammar "
            f"(K_REV {K_REV} x sd(|revision|) knob {sd_knob_of(floor)}), "
            f"rounding {ROUNDING_PP}, {TOLERANCE_ROUNDING_MODE}, terminal sd on "
            "every horizon"
        ),
        "rulings_that_can_move_it": {
            "1_grammar_and_k_rev": (
                "yes: 32 / 10 under either house grammar or the max-based "
                "term at K 2.0; 33 / 9 under mean + 1.5 sd; 28 / 14 and "
                "27 / 15 at K 2.5 (alternatives.grammar_and_k_sweep)"
            ),
            "2_horizon_pricing": (
                "yes: 37 / 5 (age62|female|h2, age62|male|h2, "
                "age66|female|h2 promoted) under settled-sd pricing of "
                "h1 / h2"
            ),
            "3_age66_female_h1": (
                "yes if demoted on a pre-registered reason: 33 / 9; option "
                "(ii) as drafted is UNAVAILABLE AS WRITTEN"
            ),
            "4_rounding_mode": "no: 34 / 8 under both modes (one tolerance moves by a cent)",
            "5_d0_estimand": (
                "yes: a published-construct choice forces a v2 floor with an "
                "eight-category cap; the six conversion cells re-enter"
            ),
            "6_d1_editions": "only through ruling 2 (a measured settle path)",
        },
        "status": "DERIVED under the drafted knobs; pending the rulings named",
    }

    artifact: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "run": RUN_NAME,
        "reported_not_gated": True,
        "component": (
            "claiming-age distribution (#74 component CA); THRESHOLD "
            "BINDING, the packet's ceremony step 4"
        ),
        "purpose": (
            "the gate-schema derivation from the VERIFIED publication floor "
            f"{SOURCE_FLOOR_REL}: the 42 tolerance derivations in Decimal "
            "under the stated mode, the gate partition, every filed "
            "alternative recomputed and cross-checked against the floor, "
            "the rule-class frontier scan as the faithful_candidate_oc "
            "substitute, the deployed-v1 finding, the certification scope, "
            "the circularity disclosure, fit isolation naming every "
            "committed channel, the eight rulings filed and priced, the "
            "wording audit and the DRAFT gate_b2_claiming block as a "
            "string. It edits no gates.yaml byte, scores no candidate and "
            "makes no ruling."
        ),
        "does_not_do": DOES_NOT_DO,
        "source_floor": {
            "path": SOURCE_FLOOR_REL,
            "size_bytes": SOURCE_FLOOR_COMMITTED[0],
            "sha256": SOURCE_FLOOR_COMMITTED[1],
            "schema_version": floor["schema_version"],
            "built_utc": floor["build"]["built_utc"],
            "committed_at": "cd8f167280de47444164d2ab0ec11dd061b59b00 (floors v2)",
            "verified_by": VERIFICATION_REPORT,
            "read_by": "path, with size and sha256 checked before any value is read",
            "blocks_read": [
                "strata.conditional_terminal_year (sd_pp, mean_pp, sd_signed_pp, max_pp)",
                "strata.conditional_settled_years (sd_pp)",
                "power_cap.derivations[*].trend_pp_per_year",
                "power_cap.gate_eligible_tolerances_pp / report_only_tolerance_above_t_max (cross-check only)",
                "power_cap_alternatives.* (cross-check only)",
                "candidate_rules_on_the_draft_surface.* (cross-check only)",
                "deployed_v1_finding (cross-check only)",
                "reference_values_pp, fit_isolation, open_decisions, does_not_establish, age66_before_fra_transition, sources",
            ],
        },
        "scoring_frame": {
            "edition_2023": _pin(EDITION_2023_REL),
            "edition_2014": _pin(EDITION_2014_REL),
            "claiming_reference_v1": _pin(CLAIMING_REFERENCE_REL),
            "construct": "conditional (seven non-conversion categories renormalised to 100)",
            "fit_years": [fb.FIT_YEARS[0], fb.FIT_YEARS[-1]],
            "holdout_years": {"h1": 2020, "h2": 2021, "h3": 2022},
            "arithmetic": (
                "unrounded-prediction path: deviation = |predict - actual|, "
                "recorded at 4 dp, verdict on the unrounded value (the "
                "floor's candidate scan and deployed_v1_finding convention)"
            ),
        },
        "ceremony": {
            "step": (
                "4 of the packet's claiming sequence (section 11): bind the "
                "derivations in tests/test_gates_derivations.py, LOCKED-HOT "
                "(the 2a lesson, gates.yaml:2925); step 5's prerequisite "
                "for the PIA gate"
            ),
            "packet": PACKET_REPORT,
            "referees": {
                "A_statistical": REFEREE_A_REPORT,
                "B_contract_and_record": REFEREE_B_REPORT,
            },
            "floors_v2": FLOORS_V2_REPORT,
            "verification": VERIFICATION_REPORT,
            "gates_yaml_untouched": True,
            "gates_yaml_stub": (
                f"{GATE_NAME} (DRAFT as a string in draft_gates_yaml_fragment; "
                "not in gates.yaml)"
            ),
            "next": (
                "adversarial referee round on these bound thresholds -> the "
                "rulings -> verification -> ratifying merge with the "
                f"{MARKER} flip and the live-file guard tests retired"
            ),
        },
        "derivation_convention": {
            "tolerance": (
                "quantize(revision_term_pp + |trend_pp_per_year| * horizon_years "
                "+ rounding_pp, 2 decimals, ROUND_HALF_UP) in Decimal on the "
                "exact decimals the knobs were written as"
            ),
            "revision_term_drafted": "K_REV * sd_knob; sd_knob = round(strata.conditional_terminal_year.sd_pp, 4)",
            "k_rev": K_REV,
            "sd_knob_pp": sd_knob_of(floor),
            "sd_full_precision_pp": floor["strata"][
                "conditional_terminal_year"
            ]["sd_pp"],
            "revision_term_pp": round(K_REV * sd_knob_of(floor), 6),
            "rounding_pp": ROUNDING_PP,
            "t_max_pp": T_MAX_PP,
            "rounding_mode": TOLERANCE_ROUNDING_MODE,
            "decimals": TOLERANCE_DECIMALS,
            "trend_estimator": floor["power_cap"]["knobs"]["trend_estimator"],
            "fit_window": floor["power_cap"]["knobs"]["fit_window"],
            "horizon_years": list(HORIZONS),
            "cell_name_rule": "'<category>|<sex>|h<horizon>' (the floor's and the packet's)",
            "cell_order_equals_floor_derivations_order": cell_order()
            == list(floor["power_cap"]["derivations"]),
        },
        "cell_order": cell_order(),
        "reference_values_pp": floor["reference_values_pp"],
        "tolerance_derivations": draft,
        "gate_partition": gate_partition,
        "gated_surface": {
            "tolerances_pp": gated,
            "reference_values_pp": {
                c: floor["reference_values_pp"]["gate_eligible"][c]
                for c in part["gate_eligible"]
            },
        },
        "alternatives": alt,
        "faithful_candidate_oc_substitute": scan,
        "deployed_v1_finding": finding,
        "certification_scope": scope,
        "temporal_holdout_circularity_disclosure": circularity_disclosure(),
        "fit_isolation": iso,
        "gates_yaml_citations": citations,
        "packet_reconciliation_carried": floor["packet_reconciliation"],
        "age66_before_fra_transition_carried": floor[
            "age66_before_fra_transition"
        ],
        "floor_does_not_establish_carried": floor["does_not_establish"],
        "flip_plan": flip_plan(),
        "record_hygiene": {
            "R1_report_footer": (
                "the threshold-binding report's footer body is computed "
                "literally ABOVE its `## Footer -- integrity` heading "
                "(verifier R1: the v2 report's footer was cut above the "
                "`---` rule instead)"
            ),
            "R2_per_rule_mean_convention": scan["per_rule_mean_convention_R2"],
            "R3_corrected_build_report_section_0b": {
                "rows_missing_from_the_map": [
                    "the section 0 table and tier counts (status update)",
                    "the section 3.1 typed-status paragraph (addition)",
                    "the section 3.2 blob-pin rewrite (update)",
                    "the section 6 bullets and the section 7 v2 paragraph (update)",
                ],
                "disposition": (
                    "LEFT AS IS: appending rows would move the report's "
                    "size and sha256, which the floors v2 report (section 0) "
                    "and the verification (section 0 table) both pin; the "
                    "four rows are recorded here and in the threshold-"
                    "binding report instead"
                ),
            },
            "R5_leaf_counts": (
                "v2's 2,292 / 4,862 include build.built_utc; excluding it "
                "gives 2,291 / 4,861; no diff statement changes"
            ),
        },
        "open_questions_for_the_ceremony": open_questions(floor, alt, scan),
        "draft_gates_yaml_fragment": fragment_meta,
        "revision_pins": {
            "populace_dynamics_sha": _git_sha(ROOT),
            "source_floor_sha256": SOURCE_FLOOR_COMMITTED[1],
            "source_floor_size_bytes": SOURCE_FLOOR_COMMITTED[0],
            "floor_builder_sha256": _sha_of_file(ROOT / FLOOR_BUILDER_REL),
            "gate_builder_sha256": _sha_of_file(Path(__file__).resolve()),
            "edition_2023_sha256": floor["sources"]["edition_2023"]["sha256"],
            "gates_yaml_git_blob_for_the_citations": GATES_YAML_BLOB_AT_BINDING,
            "gates_yaml_pin_semantics": citations["pin_semantics"],
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        },
        "build": {
            "built_by": "scripts/build_claiming_gate_floors_v1.py",
        },
    }
    audit = wording_audit(fragment, json.dumps(artifact), floor)
    if not audit["forbidden_words_absent_from_fragment"]:
        raise RuntimeError(
            f"forbidden word in the draft block: {audit['forbidden_word_counts']}"
        )
    if not audit["forbidden_words_absent_from_artifact"]:
        raise RuntimeError(
            f"forbidden word in the artifact: {audit['forbidden_word_counts']}"
        )
    if not audit["all_required_phrases_present"]:
        raise RuntimeError(
            "required phrase missing: "
            + str(
                [
                    c["item"]
                    for c in audit["required_phrases"]
                    if not c["holds"]
                ]
            )
        )
    artifact["wording_audit"] = audit
    artifact["elapsed_seconds"] = round(time.time() - started, 1)
    return artifact


def main() -> None:
    artifact = run(verbose=True)
    ARTIFACT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {ARTIFACT_PATH} ({ARTIFACT_PATH.stat().st_size} bytes)")
    frag = artifact["draft_gates_yaml_fragment"]
    print(
        f"draft block: {frag['n_lines']} lines, {frag['n_bytes']} bytes, "
        f"sha256 {frag['text_sha256']}"
    )


if __name__ == "__main__":
    main()
