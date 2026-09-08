"""Per-rule coverage of the statutory benefit oracle (#74, component SF).

This builds ``runs/pia_rule_coverage_v1.json`` -- a REPORTED, not gated,
artifact. Changes no gate. It exists because the DRAFT
``gate_b2_pia_oracle`` packet (lane ``cap-claiming-pia-gates``) scores a
per-rule coverage partition that no committed artifact carried: the
packet's partition was computed in that lane and labelled as such.

What this artifact answers, for every statutory rule the oracle
implements:

* which of the 240 committed cross-engine cases exercise it
  (``runs/pia_cross_engine_v1.json``);
* which of the 10 committed SSA worked examples exercise it
  (``runs/aux_benefit_examples_v1.json``);
* which supporting cases exercise it (the 40-case policyengine-us PIA
  foundation, the 36-row couple grid, the 9-row survivor grid) and
  which committed tests assert it;
* and which rules have **zero** case coverage.

It also quotes the packet's proposed definition of ``gates.yaml``'s
phrase *"benefit formulas earn per-rule 'computes exactly' status"* --
which occurs exactly once in the whole file, in ``gate_2.description``,
with no definition, no cell and no test anywhere. The definition is
quoted as a PROPOSAL. This artifact neither adopts nor ratifies it.

No engine is executed here. Every number is read or derived from
committed bytes; the cross-engine and policyengine-us figures are the
committed artifacts' own, and the repo's existing tests
(``tests/ss/``) are the only thing that runs either engine.

What the v2 revision adds (the two adversarial referees' lists)
===============================================================
* The household consumer is named correctly (``CoupleBenefit.total``;
  the v1 artifact's ``CoupleBenefits`` exists nowhere) and the consumer
  symbols are pinned by ``ast``, not by substring.
* The checkable E3 bases are DERIVED and recorded as data a test
  re-runs: R8 (no test in ``tests/ss/`` calls ``early_reduction(0)``),
  R4 (the one direct ``aime()`` test builds a 40-entry history, so the
  zero pad is never reached) and R9 (the ``credited <= 0`` branch is
  unreachable for every FRA in the committed schedule). Every status
  label is disclosed as the builder's reading of derived evidence.
* The typed bend-point pairs are pinned to committed bytes: each pair
  reproduces all 120 committed PIAs of its cohort from the committed
  AIMEs, and no neighbouring integer pair does; the 2020 pair's lack of
  an SSA-anchor test is disclosed.
* The ``gates.yaml`` citation is pinned to a git blob so the future
  gate commit does not break the artifact; the sequencing constraint
  that remains is recorded.
* ``NOT_IMPLEMENTED_PATTERNS`` widened; ``_spans`` fails loudly on a
  duplicate function or class name.

Run from the repository root::

    .venv/bin/python scripts/build_pia_rule_coverage.py
"""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "runs" / "pia_rule_coverage_v1.json"

BENEFITS_REL = "src/populace_dynamics/ss/benefits.py"
PARAMS_REL = "src/populace_dynamics/ss/params.py"
SS_INIT_REL = "src/populace_dynamics/ss/__init__.py"
HOUSEHOLD_REL = "src/populace_dynamics/household.py"
CROSS_ENGINE_REL = "runs/pia_cross_engine_v1.json"
AUX_REL = "runs/aux_benefit_examples_v1.json"
TEST_CROSS_ENGINE_REL = "tests/ss/test_cross_engine.py"
TEST_AUX_REL = "tests/ss/test_aux_benefits.py"
TEST_BENEFITS_REL = "tests/ss/test_benefits.py"
TEST_CLAIMING_REL = "tests/test_claiming.py"
GATES_REL = "gates.yaml"

SCHEMA_VERSION = "pia_rule_coverage.v1"
RUN = "pia_rule_coverage_v1"

PACKET = "cap-claiming-pia-gates REPORT.md (2026-09-06, drafting lane)"

#: Bend points at the two committed eligibility years, as asserted by
#: tests/ss/test_cross_engine.py::test_all_three_pia_brackets_exercised.
#: TYPED here (referee B, D6); pinned to committed bytes by
#: bend_points_provenance, which checks that each pair reproduces every
#: committed PIA of its cohort from the committed AIMEs.
BEND_POINTS = {"2020": (960.0, 5785.0), "2026": (1286.0, 7749.0)}
#: 415(a)(1)(A) bracket factors, as typed in tests/ss/test_benefits.py.
PIA_FACTORS = (0.90, 0.32, 0.15)
#: SSA-anchor tests for each typed pair (None where the repo has none).
BEND_POINT_ANCHOR_TESTS = {
    "2020": None,
    "2026": (
        "tests/ss/test_benefits.py::"
        "test_2026_bend_points_match_ssa_determination"
    ),
}

#: The gates.yaml blob this artifact cites (referee B, D7). The citation
#: is pinned to the blob, not to the working tree, so the gate commit
#: that later inserts gate_b2_pia_oracle does not change this artifact's
#: bytes; the builder reads the blob from the git object store when the
#: working tree has moved on.
GATES_YAML_BLOB_SHA1 = "b0c39af1e13a705f90b85d3e6b9a91e1d3c5485c"
COMPUTES_EXACTLY_PHRASE = "computes exactly"
COMPUTES_EXACTLY_LINE = 642

#: 415(b)(2)(B) computation-year count, hard-coded in the oracle.
COMPUTATION_YEARS = 35

#: The patterns whose absence establishes the not-implemented list.
NOT_IMPLEMENTED_PATTERNS = {
    "family_maximum": (
        "family_max",
        "familyMax",
        "maximum_family_benefit",
        "fam_max",
    ),
    "wep_gpo": ("windfall", "WEP", "GPO", "government_pension"),
    "retirement_earnings_test": ("earnings_test", "retirement_earnings"),
    "special_minimum_pia": ("special_minimum",),
    "cola_applied_to_pia": ("cola", "COLA"),
}
#: cola/COLA is searched in ss/ only; the rest across the whole package.
COLA_SEARCH_ROOT = "src/populace_dynamics/ss"
PACKAGE_SEARCH_ROOT = "src/populace_dynamics"


# --------------------------------------------------------------------------
# Committed-byte helpers
# --------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text())


def _spans(relative: str) -> dict[str, dict[str, Any]]:
    """Line spans of every symbol in a module, read with ``ast``.

    Code references in this artifact are DERIVED from the source, not
    typed, so a reproduction test re-derives them rather than trusting
    a hand-copied line number.
    """
    tree = ast.parse((ROOT / relative).read_text())
    out: dict[str, dict[str, Any]] = {}

    def record(name: str, node: ast.AST, kind: str) -> None:
        if name in out and out[name]["kind"] in ("function", "class"):
            raise ValueError(
                f"{relative}: duplicate {kind} name {name!r} at lines "
                f"{out[name]['first_line']} and {node.lineno}; a span "
                "keyed by bare name would silently relabel a rule"
            )
        out[name] = {
            "module": relative,
            "symbol": name,
            "kind": kind,
            "first_line": node.lineno,
            "last_line": getattr(node, "end_lineno", node.lineno),
        }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            record(node.name, node, "function")
        elif isinstance(node, ast.ClassDef):
            record(node.name, node, "class")
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            out.setdefault(
                node.target.id,
                {
                    "module": relative,
                    "symbol": node.target.id,
                    "kind": "field",
                    "first_line": node.lineno,
                    "last_line": node.end_lineno or node.lineno,
                },
            )
        elif isinstance(node, ast.Assign) and isinstance(
            node.targets[0], ast.Name
        ):
            out.setdefault(
                node.targets[0].id,
                {
                    "module": relative,
                    "symbol": node.targets[0].id,
                    "kind": "constant",
                    "first_line": node.lineno,
                    "last_line": node.end_lineno or node.lineno,
                },
            )
    return out


def _test_names(relative: str) -> set[str]:
    """Every ``test_*`` function name defined in a test module."""
    tree = ast.parse((ROOT / relative).read_text())
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test")
    }


def _grep_absent(root: str, patterns: tuple[str, ...]) -> dict[str, Any]:
    """Record that no ``.py`` file under ``root`` contains any pattern."""
    hits: list[str] = []
    for path in sorted((ROOT / root).rglob("*.py")):
        text = path.read_text()
        for pattern in patterns:
            if pattern in text:
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{pattern}")
    return {
        "search_root": root,
        "patterns": list(patterns),
        "n_files_searched": len(list((ROOT / root).rglob("*.py"))),
        "hits": hits,
        "absent": not hits,
    }


def _git_blob_sha1(raw: bytes) -> str:
    """The git object id of ``raw`` as a blob (content-addressed)."""
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _gates_yaml_bytes() -> bytes:
    """The bytes of the PINNED gates.yaml blob.

    The working tree is used when its blob matches the pin; otherwise
    the blob is read from the git object store, so a later gates.yaml
    (the one that inserts the gate block) leaves this artifact's bytes
    unchanged. A missing blob is an error, never a silent re-pin.
    """
    on_disk = (ROOT / GATES_REL).read_bytes()
    if _git_blob_sha1(on_disk) == GATES_YAML_BLOB_SHA1:
        return on_disk
    result = subprocess.run(
        ["git", "cat-file", "blob", GATES_YAML_BLOB_SHA1],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or _git_blob_sha1(result.stdout) != (
        GATES_YAML_BLOB_SHA1
    ):
        raise RuntimeError(
            f"gates.yaml blob {GATES_YAML_BLOB_SHA1} is neither the "
            "working-tree file nor retrievable from the git object store"
        )
    return result.stdout


def _gates_citation() -> dict[str, Any]:
    raw = _gates_yaml_bytes()
    lines = raw.decode("utf-8").splitlines()
    occurrences = [
        {"line": index + 1, "text": line.strip()}
        for index, line in enumerate(lines)
        if COMPUTES_EXACTLY_PHRASE in line
    ]
    return {
        "path": GATES_REL,
        "git_blob_sha1": GATES_YAML_BLOB_SHA1,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "phrase": COMPUTES_EXACTLY_PHRASE,
        "occurrences": occurrences,
        "n_occurrences": len(occurrences),
        "cited_line": COMPUTES_EXACTLY_LINE,
        "cited_line_text": lines[COMPUTES_EXACTLY_LINE - 1].strip(),
        "gate_b2_pia_oracle_present_in_pinned_blob": (
            "gate_b2_pia_oracle" in raw.decode("utf-8")
        ),
        "pin_note": (
            "This citation is pinned to a git BLOB of gates.yaml, not "
            "to the working tree (referee B, D7). The tests rescan the "
            "pinned blob (from the working tree while it matches, from "
            "the git object store once it has moved on), so the gate "
            "commit that inserts gate_b2_pia_oracle -- and adds the "
            "phrase 'computes exactly' to a new block -- changes "
            "neither this artifact nor the tests that pin it. What that "
            "commit MUST still do is retire the two 'gate name absent "
            "from gates.yaml' assertions (tests/test_pia_rule_coverage."
            "py and tests/test_claiming_publication_floor.py), which "
            "read the LIVE file by design and fail the moment either "
            "gate block lands; see does_not_establish."
        ),
    }


# --------------------------------------------------------------------------
# Derived E3 bases and the typed bend points' pin (v2)
# --------------------------------------------------------------------------
TESTS_SS_ROOT = "tests/ss"


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _call_sites(root: str, function_name: str) -> list[dict[str, Any]]:
    """Every call of ``function_name`` in the ``.py`` files under
    ``root``, with its enclosing function and its literal first
    argument if the first argument is a constant."""
    sites: list[dict[str, Any]] = []
    for path in sorted((ROOT / root).rglob("*.py")):
        tree = ast.parse(path.read_text())
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef):
                continue
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and _call_name(node) == function_name
                ):
                    first = node.args[0] if node.args else None
                    sites.append(
                        {
                            "module": path.relative_to(ROOT).as_posix(),
                            "enclosing_function": function.name,
                            "line": node.lineno,
                            "first_argument_literal": (
                                first.value
                                if isinstance(first, ast.Constant)
                                else None
                            ),
                            "first_argument_is_literal": isinstance(
                                first, ast.Constant
                            ),
                        }
                    )
    return sites


def _literal_range_lengths(root: str, module: str, function_name: str):
    """Lengths of every ``range(a, b)`` with integer literals inside the
    named function (a static read of how a test builds its history)."""
    tree = ast.parse((ROOT / module).read_text())
    lengths: list[int] = []
    for function in ast.walk(tree):
        if not (
            isinstance(function, ast.FunctionDef)
            and function.name == function_name
        ):
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and _call_name(node) == "range"
                and len(node.args) == 2
                and all(
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, int)
                    for arg in node.args
                )
            ):
                lengths.append(node.args[1].value - node.args[0].value)
    return lengths


def _module_int_constant(relative: str, name: str) -> int:
    """The integer a module-level ``NAME = <int expr>`` evaluates to,
    read with ``ast`` (products of literals allowed, e.g. ``70 * 12``)."""
    tree = ast.parse((ROOT / relative).read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return int(
                eval(compile(ast.Expression(node.value), "<ast>", "eval"))
            )
    raise KeyError(f"{relative}: no module-level constant {name}")


def _dataclass_field_default(relative: str, name: str) -> Any:
    tree = ast.parse((ROOT / relative).read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and isinstance(node.value, ast.Constant)
        ):
            return node.value.value
    raise KeyError(f"{relative}: no annotated field {name} with a literal")


def _r8_basis_derivation() -> dict[str, Any]:
    sites = _call_sites(TESTS_SS_ROOT, "early_reduction")
    literals = sorted(
        {
            site["first_argument_literal"]
            for site in sites
            if site["first_argument_is_literal"]
        }
    )
    return {
        "claim": (
            "no test in tests/ss/ asserts early_reduction(0), so the "
            "months_early <= 0 early-return branch is reached by no test"
        ),
        "derivation_kind": (
            "static ast read of every early_reduction(...) call under "
            "tests/ss/: the literal first argument of each call"
        ),
        "search_root": TESTS_SS_ROOT,
        "call_sites": sites,
        "n_call_sites": len(sites),
        "first_argument_literals": literals,
        "every_first_argument_is_a_literal": all(
            site["first_argument_is_literal"] for site in sites
        ),
        "zero_or_negative_asserted": any(
            isinstance(v, (int, float)) and v <= 0 for v in literals
        ),
        "claim_holds": not any(
            isinstance(v, (int, float)) and v <= 0 for v in literals
        ),
    }


def _r4_basis_derivation() -> dict[str, Any]:
    sites = _call_sites(TESTS_SS_ROOT, "aime")
    per_site = []
    for site in sites:
        lengths = _literal_range_lengths(
            TESTS_SS_ROOT, site["module"], site["enclosing_function"]
        )
        per_site.append(
            {
                **site,
                "literal_range_lengths_in_enclosing_test": lengths,
                "min_history_length_if_literal": (
                    min(lengths) if lengths else None
                ),
            }
        )
    every_ge = all(
        row["min_history_length_if_literal"] is not None
        and row["min_history_length_if_literal"] >= COMPUTATION_YEARS
        for row in per_site
    )
    return {
        "claim": (
            "the short-history zero-pad branch of aime() is reached by "
            "no test in tests/ss/"
        ),
        "derivation_kind": (
            "static ast read of every aime(...) call under tests/ss/ "
            "and of the integer-literal range(a, b) calls inside each "
            "enclosing test (the history the test builds); a dynamic "
            "history length would require executing the tests"
        ),
        "search_root": TESTS_SS_ROOT,
        "computation_years": COMPUTATION_YEARS,
        "call_sites": per_site,
        "n_call_sites": len(sites),
        "every_direct_aime_test_builds_at_least_n_years": every_ge,
        "claim_holds": bool(per_site) and every_ge,
    }


def _r9_basis_derivation(doc_2023: dict[str, Any]) -> dict[str, Any]:
    age_70_months = _module_int_constant(BENEFITS_REL, "_AGE_70_MONTHS")
    max_delayed_months = _dataclass_field_default(
        PARAMS_REL, "max_delayed_months"
    )
    schedule = doc_2023["fra_schedule"]["schedule"]
    fra_values = sorted({int(row["fra_months"]) for row in schedule})
    windows = {
        str(fra): min(max_delayed_months, age_70_months - fra)
        for fra in fra_values
    }
    return {
        "claim": (
            "the credited <= 0 branch of delayed_credit is unreachable "
            "for every FRA in the committed schedule"
        ),
        "derivation_kind": (
            "arithmetic on committed bytes: window = min("
            "max_delayed_months, _AGE_70_MONTHS - fra); credited = "
            "min(months_late, window) with months_late > 0 (the earlier "
            "return handles months_late <= 0), so credited <= 0 iff "
            "window <= 0 iff fra >= _AGE_70_MONTHS. The FRA schedule is "
            "SSA's own (Table 6.B5.1 footnote a) as committed in the "
            "2023 edition; tests/test_claiming.py::"
            "test_fra_footnote_schedule_matches_oracle asserts it "
            "equals the oracle's policyengine-us-loaded schedule."
        ),
        "age_70_months": age_70_months,
        "age_70_months_source": f"{BENEFITS_REL}::_AGE_70_MONTHS (ast)",
        "max_delayed_months": max_delayed_months,
        "max_delayed_months_source": (
            f"{PARAMS_REL}::SSAParameters.max_delayed_months default (ast)"
        ),
        "fra_schedule_source": (
            "data/external/ssa_claim_ages_2023supplement.json::fra_schedule"
        ),
        "fra_months_values": fra_values,
        "max_fra_months": max(fra_values),
        "window_months_by_fra": windows,
        "min_window_months": min(windows.values()),
        "branch_reachable_iff_fra_months_at_least": age_70_months,
        "claim_holds": min(windows.values()) >= 1,
    }


def _pia(aime_value: float, first: float, second: float) -> float:
    """415(a)(1)(A) with the 415(g) dime floor, on integer AIME."""
    amount = (
        PIA_FACTORS[0] * min(aime_value, first)
        + PIA_FACTORS[1] * max(0.0, min(aime_value, second) - first)
        + PIA_FACTORS[2] * max(0.0, aime_value - second)
    )
    return math.floor(amount * 10.0 + 1e-9) / 10.0


def _bend_points_provenance(cross: dict[str, Any]) -> dict[str, Any]:
    """Pin the TYPED bend-point pairs to committed bytes (referee B, D6):
    each pair must reproduce every committed PIA of its cohort from the
    committed AIME, and no neighbouring integer pair may."""
    rows = cross["workers"]
    by_cohort: dict[str, Any] = {}
    for cohort, (first, second) in BEND_POINTS.items():
        cohort_rows = [r for r in rows if str(r["cohort"]) == cohort]
        reproduced = sum(
            1
            for r in cohort_rows
            if abs(_pia(r["aime_oracle"], first, second) - r["pia_oracle"])
            < 1e-9
        )
        neighbours = [
            [first + d1, second + d2]
            for d1 in range(-3, 4)
            for d2 in range(-3, 4)
            if (d1, d2) != (0, 0)
            and all(
                abs(
                    _pia(r["aime_oracle"], first + d1, second + d2)
                    - r["pia_oracle"]
                )
                < 1e-9
                for r in cohort_rows
            )
        ]
        by_cohort[cohort] = {
            "typed_pair": [first, second],
            "n_rows": len(cohort_rows),
            "n_rows_reproduced_to_the_dime": reproduced,
            "reproduces_every_committed_pia": reproduced == len(cohort_rows),
            "neighbouring_integer_pairs_within_3_dollars_also_reproducing_all_rows": neighbours,
            "pair_is_unique_within_3_dollars": not neighbours,
            "ssa_anchor_test": BEND_POINT_ANCHOR_TESTS[cohort],
        }
    return {
        "note": (
            "BEND_POINTS is TYPED in this builder (copied from "
            "tests/ss/test_cross_engine.py::test_all_three_pia_brackets_"
            "exercised), not loaded from policyengine-us. It is pinned "
            "to committed bytes here: each typed pair, run through the "
            "90 / 32 / 15 brackets and the dime floor, reproduces every "
            "committed pia_oracle of its cohort from the committed "
            "aime_oracle, and no integer pair within three dollars of "
            "it does. The 2026 pair additionally has an SSA-anchor test; "
            "the 2020 pair (960 / 5785) has none in the repo, which is "
            "disclosed rather than repaired."
        ),
        "pia_factors_typed": list(PIA_FACTORS),
        "by_cohort": by_cohort,
        "every_pair_reproduces_its_cohort": all(
            block["reproduces_every_committed_pia"]
            for block in by_cohort.values()
        ),
        "pairs_without_an_ssa_anchor_test": sorted(
            cohort
            for cohort, block in by_cohort.items()
            if block["ssa_anchor_test"] is None
        ),
    }


def _consumer_symbols(household_spans: dict[str, dict[str, Any]]) -> dict:
    """The household consumer's symbols, by ast (referee B, F1)."""
    return {
        "class": household_spans["CoupleBenefit"],
        "summation_property": household_spans["total"],
        "function": household_spans["couple_benefit"],
        "qualified_summation_symbol": "CoupleBenefit.total",
        "symbol_names_derived_by_ast": [
            "CoupleBenefit",
            "total",
            "couple_benefit",
        ],
        "name_the_v1_artifact_used": "CoupleBenefits",
        "name_the_v1_artifact_used_exists": "CoupleBenefits"
        in household_spans,
        "packet_name": "couple_benefits",
        "packet_name_exists": "couple_benefits" in household_spans,
    }


# --------------------------------------------------------------------------
# Evidence inventories, derived from the committed artifacts
# --------------------------------------------------------------------------
def _cross_engine_inventory(cross: dict[str, Any]) -> dict[str, Any]:
    rows = cross["workers"]
    shapes: dict[str, int] = {}
    for row in rows:
        shapes[row["shape"]] = shapes.get(row["shape"], 0) + 1

    brackets: dict[str, Any] = {}
    for cohort, (first, second) in BEND_POINTS.items():
        cohort_rows = [r for r in rows if str(r["cohort"]) == cohort]
        aimes = [r["aime_oracle"] for r in cohort_rows]
        brackets[cohort] = {
            "n": len(cohort_rows),
            "bend_points": [first, second],
            "n_aime_zero": sum(1 for a in aimes if a == 0),
            "n_first_bracket_only": sum(1 for a in aimes if 0 < a <= first),
            "n_reaching_second_bracket": sum(
                1 for a in aimes if first < a <= second
            ),
            "n_reaching_third_bracket": sum(1 for a in aimes if a > second),
            "min_aime": min(aimes),
            "max_aime": max(aimes),
            "all_three_brackets_exercised": (
                any(0 < a <= first for a in aimes)
                and any(first < a <= second for a in aimes)
                and any(a > second for a in aimes)
            ),
        }

    dimes = [round(r["pia_oracle"] * 10) for r in rows]
    return {
        "artifact": CROSS_ENGINE_REL,
        "n_cases": cross["n_workers"],
        "engine_revision": cross["engine_revision"],
        "pe_us_revision": cross["pe_us_revision"],
        "seed": cross["seed"],
        "agreement_tolerance_dollars": cross["agreement_tolerance_dollars"],
        "max_abs_diff_dollars": cross["max_abs_diff_dollars"],
        "n_exact_to_cent": cross["n_exact_to_cent"],
        "cohorts": cross["cohorts"],
        "worker_design": cross["worker_design"],
        "declared_exercises": cross["exercises"],
        "notes": cross["notes"],
        "shape_counts": dict(sorted(shapes.items())),
        "n_distinct_shapes": len(shapes),
        "bracket_occupancy": brackets,
        "dime_floor": {
            "n_pia_values_on_an_exact_dime": sum(
                1
                for row, dime in zip(rows, dimes, strict=True)
                if abs(dime - row["pia_oracle"] * 10) < 1e-6
            ),
            "n_pia_values_not_a_whole_dollar": sum(
                1
                for row in rows
                if abs(row["pia_oracle"] - round(row["pia_oracle"])) > 1e-9
            ),
            "note": (
                "Every committed PIA is an exact multiple of ten cents, "
                "and most are not whole dollars, so the 415(g) floor is "
                "non-vacuous across the case set."
            ),
        },
        "row_fields": sorted(rows[0]),
        "what_the_rows_cannot_show": (
            "The rows carry id, cohort, shape, aime_oracle, aime_engine, "
            "pia_oracle, pia_engine and abs_diff only. They carry no "
            "earnings history, so per-row wage-base clipping and "
            "per-row indexation are NOT determinable from the committed "
            "bytes; they carry no claiming factor and no auxiliary "
            "amount, so every rule from 402(q) onward is invisible to "
            "this artifact."
        ),
    }


def _worked_example_inventory(aux: dict[str, Any]) -> dict[str, Any]:
    block = aux["ssa_worked_examples"]
    rows = []
    for group in ("spousal", "survivor"):
        for example in block[group]:
            inputs = example["inputs"]
            base = inputs.get("worker_pia", inputs.get("deceased_pia"))
            rows.append(
                {
                    "group": group,
                    "name": example["name"],
                    "citation": example["citation"],
                    "inputs": inputs,
                    "our_output": example["our_output"],
                    "expected": example["expected"],
                    "abs_deviation": abs(
                        example["our_output"] - example["expected"]
                    ),
                    "base_pia": base,
                    "expected_over_base_pia": (
                        round(example["expected"] / base, 8) if base else None
                    ),
                    "note": example["note"],
                }
            )
    return {
        "artifact": AUX_REL,
        "n_examples": len(rows),
        "max_abs_deviation": block["max_abs_deviation"],
        "scope_note": block["note"],
        "examples": rows,
        "anchor_classification": {
            "source": PACKET,
            "status": "proposal_not_ratified",
            "rule_as_stated_by_the_packet": (
                "a row counts toward E2 only if its `expected` is an "
                "SSA-PUBLISHED figure; a row whose `expected` is "
                "recomputed from the same formula tests BRANCH "
                "SELECTION, not the correctness of the rule"
            ),
            "packet_published_percentage_anchors": [
                "spouse_at_fra_half_pia",
                "spouse_at_62_fra67",
                "spouse_at_62_fra66",
                "widow_at_fra_full_pia",
                "widow_at_60_floor",
                "widow_at_62_fra66",
                "rib_lim_82_5_floor",
            ],
            "packet_arithmetic_or_branch_selection": [
                "spouse_dual_entitlement_excess",
                "rib_lim_deceased_actual_higher",
                "drc_pass_through",
            ],
            "adjudication_note": (
                "The split is the packet's reading of each row's own "
                "citation and note, not a measurement. "
                "expected_over_base_pia is computed above so a referee "
                "re-derives the ratio and adjudicates the "
                "classification independently -- drc_pass_through in "
                "particular has a ratio of 1.32 whose 32 percent IS "
                "published, while the product is the oracle's own."
            ),
        },
    }


def _foundation_inventory(aux: dict[str, Any]) -> dict[str, Any]:
    foundation = aux["pe_us_pia_foundation"]
    cases = foundation["cases"]
    reduced = [case for case in cases if case["our_factor"] < 1.0]
    credited = [case for case in cases if case["our_factor"] > 1.0]
    at_fra = [case for case in cases if case["our_factor"] == 1.0]
    return {
        "artifact": AUX_REL,
        "oracle": foundation["oracle"],
        "oracle_available_at_build": foundation["oracle_available"],
        "n_cases": foundation["n_cases"],
        "eligibility_year": foundation["year"],
        "aime_values": sorted({case["aime"] for case in cases}),
        "claim_ages": sorted({case["claim_age"] for case in cases}),
        "birth_years": sorted({case["birth_year"] for case in cases}),
        "max_pia_abs_deviation": foundation["max_pia_abs_deviation"],
        "max_factor_abs_deviation": foundation["max_factor_abs_deviation"],
        "factor_coverage": {
            "derivation": (
                "claiming.benefit_factor short-circuits: it calls "
                "402(q) early_reduction only when the claim precedes "
                "FRA, and 402(w) delayed_credit only when it follows "
                "FRA. So a case's committed our_factor says which rule "
                "it invoked -- below 1 the reduction, above 1 the "
                "credit, exactly 1 neither."
            ),
            "n_cases_invoking_402q_reduction": len(reduced),
            "n_cases_invoking_402w_credit": len(credited),
            "n_cases_exactly_at_fra": len(at_fra),
            "n_cases_at_claim_age_62": sum(
                1 for case in cases if case["claim_age"] == 62
            ),
            "distinct_factors": [
                list(row)
                for row in sorted(
                    {
                        (
                            case["birth_year"],
                            case["claim_age"],
                            round(case["our_factor"], 8),
                        )
                        for case in cases
                    }
                )
            ],
        },
        "residual_note": foundation["residual_note"],
        "residual_note_is_quoted_not_verified": (
            "The float32 attribution is the committed artifact's own "
            "note, read and quoted. This build executed no "
            "policyengine-us Simulation and did not re-derive it."
        ),
    }


def _grid_inventory(aux: dict[str, Any]) -> dict[str, Any]:
    couple = aux["couple_grid"]
    survivor = aux["survivor_grid"]
    both_excess = [
        row
        for row in couple
        if row["excess_spousal_worker"] > 0
        and row["excess_spousal_spouse"] > 0
    ]
    return {
        "couple_grid": {
            "n_rows": len(couple),
            "worker_pia_values": sorted({r["worker_pia"] for r in couple}),
            "spouse_pia_values": sorted({r["spouse_pia"] for r in couple}),
            "worker_claim_ages": sorted(
                {r["worker_claim_age"] for r in couple}
            ),
            "spouse_claim_ages": sorted(
                {r["spouse_claim_age"] for r in couple}
            ),
            "n_rows_with_worker_excess": sum(
                1 for r in couple if r["excess_spousal_worker"] > 0
            ),
            "n_rows_with_spouse_excess": sum(
                1 for r in couple if r["excess_spousal_spouse"] > 0
            ),
            "n_rows_with_both_spouses_drawing_an_excess": len(both_excess),
            "gap": (
                "No row has BOTH spouses drawing an excess, so the "
                "symmetric dual-entitlement case is unexercised."
            ),
        },
        "survivor_grid": {
            "n_rows": len(survivor),
            "distinct_own_deceased_pia_pairs": [
                list(pair)
                for pair in sorted(
                    {
                        (r["surviving_own_pia"], r["deceased_pia"])
                        for r in survivor
                    }
                )
            ],
            "deceased_claim_ages": sorted(
                {r["deceased_claim_age"] for r in survivor}
            ),
            "survivor_claim_ages": sorted(
                {r["survivor_claim_age"] for r in survivor}
            ),
            "deceased_own_factors": sorted(
                {r["deceased_own_factor"] for r in survivor}
            ),
            "gap": (
                "Every row sits at a single (own 800, deceased 2200) "
                "PIA pair, so the dual-entitlement max() is exercised "
                "at one level ratio only."
            ),
        },
    }


# --------------------------------------------------------------------------
# The rule inventory
# --------------------------------------------------------------------------
def _rule_inventory(
    benefits_spans: dict[str, dict[str, Any]],
    params_spans: dict[str, dict[str, Any]],
    cross_inventory: dict[str, Any],
    foundation: dict[str, Any],
    basis_derivations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    n_cases = cross_inventory["n_cases"]
    shapes = cross_inventory["shape_counts"]
    clipped_shapes = ("clipped_always", "rand_clipped_always")
    n_clipped_labelled = sum(shapes.get(name, 0) for name in clipped_shapes)
    brackets = cross_inventory["bracket_occupancy"]
    factors = foundation["factor_coverage"]

    def code(*symbols: tuple[str, dict[str, dict[str, Any]]]):
        return [spans[name] for name, spans in symbols]

    none_of_240 = {
        "n_cases": 0,
        "selector": "none",
        "derivation": (
            "the committed cross-engine rows carry aime and pia only; "
            "this rule produces neither, so no committed case "
            "exercises it"
        ),
    }

    rules: list[dict[str, Any]] = [
        {
            "id": "R1_415b1_wage_base_cap",
            "statute": "42 USC 415(b)(1)",
            "title": (
                "cap each year's creditable earnings at the "
                "contribution and benefit base"
            ),
            "code": code(("creditable_history", benefits_spans)),
            "cross_engine": {
                "n_cases": n_cases,
                "n_cases_labelled_wage_base_clipped": n_clipped_labelled,
                "clipped_shape_labels": list(clipped_shapes),
                "selector": (
                    "every case runs the cap; the shape LABEL asserts "
                    "clipping for clipped_always and "
                    "rand_clipped_always"
                ),
                "derivation": (
                    "the committed rows carry no earnings history, so "
                    "the exact number of cases in which the cap BINDS "
                    "is not determinable from committed bytes. The "
                    "shape-label count is a lower bound the artifact's "
                    "own worker_design corroborates ('wage-base-clipped "
                    "in many years')."
                ),
                "exact_binding_count_determinable": False,
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_BENEFITS_REL}::"
                "test_aime_caps_at_wage_base_and_floors_to_dollar"
            ],
            "e1": {
                "status": "satisfied",
                "basis": (
                    "executed by the Axiom engine and the oracle on all "
                    f"{n_cases} cases, agreeing to the cent"
                ),
            },
            "e2": {
                "status": "absent",
                "basis": (
                    "the wage-base series is policyengine-us-sourced; "
                    "no committed case checks a base value against an "
                    "SSA determination"
                ),
            },
            "e3": {
                "status": "both_branches_reached",
                "basis": (
                    "capped and uncapped years both occur across the "
                    "shape families; not per-row verifiable"
                ),
            },
        },
        {
            "id": "R2_415b3_nawi_indexation",
            "statute": "42 USC 415(b)(3)",
            "title": (
                "index creditable earnings by NAWI to the age-60 year; "
                "nominal at or after it"
            ),
            "code": code(("indexed_history", benefits_spans)),
            "cross_engine": {
                "n_cases": n_cases,
                "selector": "every committed cross-engine case",
                "derivation": (
                    "each worker's history spans ages 22-62, and the "
                    "indexing year is the age-60 year, which falls "
                    "inside that span; so both the 'year >= "
                    "indexing_year' branch (the age-60, 61 and 62 "
                    "years) and the 'year < indexing_year' branch (the "
                    "38 earlier years) execute for every case"
                ),
                "derivation_source": (
                    "the history span is the committed artifact's own "
                    "worker_design field ('nominal earnings for ages "
                    "22-62 (41 calendar years...)'); the indexing age "
                    "is _INDEXING_AGE in ss/benefits.py. Both cohorts "
                    "check out: birth 1958 indexes at 2018 over "
                    "1980-2020, birth 1964 at 2024 over 1986-2026."
                ),
                "branch_derivation_inputs": {
                    "history_span_ages": [22, 62],
                    "indexing_age": 60,
                    "n_years_at_or_after_indexing_year": 3,
                    "n_years_before_indexing_year": 38,
                },
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_BENEFITS_REL}::"
                "test_indexing_is_neutral_for_constant_relative_earner"
            ],
            "e1": {
                "status": "satisfied",
                "basis": f"all {n_cases} cases, agreeing to the cent",
            },
            "e2": {
                "status": "absent",
                "basis": (
                    "the only committed assertion is an internal "
                    "invariant (a constant-relative earner indexes to a "
                    "constant), not an SSA-published figure"
                ),
            },
            "e3": {
                "status": "both_branches_reached",
                "basis": "derived above from the history span",
            },
        },
        {
            "id": "R3_415b2B_computation_year_count",
            "statute": "42 USC 415(b)(2)(B)",
            "title": "the computation-year count n",
            "code": code(
                ("_COMPUTATION_YEARS", benefits_spans),
                ("aime", benefits_spans),
            ),
            "cross_engine": {
                "n_cases": n_cases,
                "n_cases_distinguishing_the_constant": 0,
                "selector": (
                    "every case executes it; none distinguishes the "
                    "oracle's constant from the engine's derived n"
                ),
                "derivation": (
                    "the committed artifact's own note records elapsed "
                    "- 5 = 35 for BOTH cohorts, so the engine's derived "
                    "n equals the oracle's hard-coded 35 in every "
                    "committed case"
                ),
                "artifact_note": cross_inventory["notes"],
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": 0,
            "tests": [],
            "e1": {
                "status": "degenerate",
                "basis": (
                    "agreement is unforced: both sides evaluate to 35 "
                    "on every committed case, so the cases cannot "
                    "separate a derived n from a constant"
                ),
            },
            "e2": {"status": "absent", "basis": "no anchor case exists"},
            "e3": {
                "status": "unexercised",
                "basis": (
                    "no committed case has n != 35, so the "
                    "domain-limited constant is never tested outside "
                    "its exact domain"
                ),
            },
        },
        {
            "id": "R4_415b_top_n_divide_and_floor",
            "statute": "42 USC 415(b)",
            "title": (
                "highest-n selection, division by n x 12, truncation to "
                "the dollar"
            ),
            "code": code(("aime", benefits_spans)),
            "cross_engine": {
                "n_cases": n_cases,
                "n_cases_reaching_the_zero_pad_branch": 0,
                "selector": (
                    "every case exercises selection, division and "
                    "truncation; NO case reaches the short-history "
                    "zero-pad branch"
                ),
                "derivation": (
                    "every committed worker's history has 41 entries "
                    "(ages 22-62, zeros included as entries), so the "
                    "top-n slice always yields exactly "
                    f"{COMPUTATION_YEARS} values and the pad is a "
                    "no-op. The all_zeros and zero_spell shapes carry "
                    "zero EARNINGS, not missing YEARS, so they do not "
                    "reach it either."
                ),
                "derivation_source": (
                    "the 41-year span is the committed artifact's own "
                    "worker_design field; that the zero shapes carry "
                    "zero-valued ENTRIES rather than absent years is "
                    "read from the committed builder "
                    "scripts/build_cross_engine_pia_artifact.py, whose "
                    "_build_workers constructs every shape as a dict "
                    "over the full year range. The committed rows "
                    "carry no history, so this is a source read, not a "
                    "row-level derivation."
                ),
                "aime_range": [
                    min(block["min_aime"] for block in brackets.values()),
                    max(block["max_aime"] for block in brackets.values()),
                ],
                "n_cases_with_zero_aime": sum(
                    block["n_aime_zero"] for block in brackets.values()
                ),
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_BENEFITS_REL}::"
                "test_aime_caps_at_wage_base_and_floors_to_dollar"
            ],
            "e1": {
                "status": "satisfied",
                "basis": f"all {n_cases} cases, agreeing to the cent",
            },
            "e2": {
                "status": "absent",
                "basis": (
                    "the only committed assertion re-derives the value "
                    "with the same formula"
                ),
            },
            "e3": {
                "status": "branch_unexercised",
                "basis": (
                    "the short-history zero-pad branch is reached by no "
                    "committed cross-engine case and by no test in "
                    "tests/ss/. Other in-repo callers of aime() exist "
                    "(populace_dynamics.estimates.ledgers, "
                    "populace_dynamics.data.couple_earnings); none is "
                    "part of a registered case set here."
                ),
                "basis_derivation": basis_derivations["R4"],
            },
        },
        {
            "id": "R5_415a1A_pia_brackets",
            "statute": "42 USC 415(a)(1)(A)",
            "title": "the 90 / 32 / 15 percent brackets",
            "code": code(("pia", benefits_spans)),
            "cross_engine": {
                "n_cases": n_cases,
                "selector": (
                    "every case; bracket occupancy computed per cohort "
                    "from the committed AIME values against the "
                    "cohort's bend points"
                ),
                "bracket_occupancy": brackets,
                "all_three_brackets_exercised_per_cohort": all(
                    block["all_three_brackets_exercised"]
                    for block in brackets.values()
                ),
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": foundation["n_cases"],
            "tests": [
                f"{TEST_CROSS_ENGINE_REL}::"
                "TestCommittedArtifact::"
                "test_all_three_pia_brackets_exercised",
                f"{TEST_BENEFITS_REL}::test_pia_worked_example_2026",
                f"{TEST_BENEFITS_REL}::"
                "test_pia_below_first_bend_point_is_90_percent",
            ],
            "e1": {
                "status": "satisfied",
                "basis": f"all {n_cases} cases, agreeing to the cent",
            },
            "e2": {
                "status": "weak",
                "basis": (
                    "test_pia_worked_example_2026 asserts 3263.20, "
                    "which is the oracle's own arithmetic from SSA's "
                    "published 2026 bend points -- the BEND POINTS are "
                    "published, the bracket total is not"
                ),
                "bend_points_note": (
                    "the bend points the occupancy is scored against are "
                    "typed in this builder and pinned to the committed "
                    "rows by evidence_inventory.cross_engine."
                    "bend_points_provenance; the 2020 pair has no "
                    "SSA-anchor test in the repo"
                ),
            },
            "e3": {
                "status": "all_branches_exercised",
                "basis": (
                    "all three brackets are occupied in both cohorts, "
                    "computed above from committed AIME values"
                ),
            },
        },
        {
            "id": "R6_415a1B_bend_points",
            "statute": "42 USC 415(a)(1)(B)",
            "title": (
                "bend points from the 1979 base amounts scaled by the "
                "NAWI ratio to 1977"
            ),
            "code": code(("bend_points", params_spans)),
            "cross_engine": {
                "n_cases": n_cases,
                "n_distinct_eligibility_years": len(BEND_POINTS),
                "eligibility_years": sorted(int(y) for y in BEND_POINTS),
                "selector": (
                    "every case resolves bend points, but at only the "
                    "two committed eligibility years"
                ),
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": foundation["n_cases"],
            "tests": [
                f"{TEST_BENEFITS_REL}::"
                "test_2026_bend_points_match_ssa_determination",
                f"{TEST_BENEFITS_REL}::"
                "test_derived_2015_bend_points_match_ssa_published",
            ],
            "e1": {
                "status": "satisfied",
                "basis": (
                    "both engines resolve bend points on all "
                    f"{n_cases} cases; params.load_ssa_parameters also "
                    "cross-checks every stored year against "
                    "policyengine-us at load time"
                ),
            },
            "e2": {
                "status": "satisfied",
                "basis": (
                    "SSA's 2026 determination (1286 / 7749) and 2015 "
                    "determination (826 / 4980) are asserted directly"
                ),
            },
            "e3": {
                "status": "partial",
                "basis": (
                    "two eligibility years carry a published anchor; "
                    "the remaining in-scope years rest on the load-time "
                    "cross-check against policyengine-us, which is not "
                    "an SSA determination"
                ),
            },
        },
        {
            "id": "R7_415g_dime_floor",
            "statute": "42 USC 415(g)",
            "title": "round the PIA down to the next lower dime",
            "code": code(("pia", benefits_spans)),
            "cross_engine": {
                "n_cases": n_cases,
                "selector": "every case",
                "dime_floor": cross_inventory["dime_floor"],
            },
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": foundation["n_cases"],
            "tests": [
                f"{TEST_CROSS_ENGINE_REL}::"
                "TestDimeFloorEpsilonIsInert::"
                "test_epsilon_never_changes_result"
            ],
            "e1": {
                "status": "satisfied",
                "basis": (
                    f"all {n_cases} cases; the engine's plain floor and "
                    "the oracle's epsilon floor agree exactly"
                ),
            },
            "e2": {
                "status": "implied",
                "basis": (
                    "no case anchors the rounding rule on its own; it "
                    "rides on R6's published bend points and the "
                    "resulting published PIA scale"
                ),
            },
            "e3": {
                "status": "exhaustive",
                "basis": (
                    "an exhaustive sweep over integer AIME 0..15,000 at "
                    "both eligibility years proves the epsilon inert"
                ),
            },
        },
        {
            "id": "R8_402q_worker_early_reduction",
            "statute": "42 USC 402(q)",
            "title": (
                "5/9 of one percent per month for the first 36 months "
                "early, 5/12 of one percent per month beyond"
            ),
            "code": code(("early_reduction", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": factors[
                "n_cases_invoking_402q_reduction"
            ],
            "pe_us_foundation_selector": (
                "the foundation cases whose committed our_factor is "
                "below 1, i.e. those that invoke the reduction"
            ),
            "tests": [
                f"{TEST_BENEFITS_REL}::"
                "test_early_reduction_at_fra_67_claiming_62"
            ],
            "e1": {
                "status": "policyengine_us_only",
                "basis": (
                    "not in the 240 (which stop at the PIA); the only "
                    "independent execution is the "
                    f"{factors['n_cases_invoking_402q_reduction']} "
                    "reduction cases of the policyengine-us foundation "
                    "block"
                ),
            },
            "e2": {
                "status": "satisfied",
                "basis": (
                    "SSA's published 30 percent reduction at 60 months "
                    "early, and 70 percent of PIA at 62 against an FRA "
                    "of 67"
                ),
            },
            "e3": {
                "status": "partial_and_one_branch_unexercised",
                "basis": (
                    "both rate brackets are reached at 60 months "
                    "early, but the months-early domain is sampled at "
                    "the foundation grid's claim ages only. The "
                    "months_early <= 0 early-return branch is NOT "
                    "reached: benefit_factor short-circuits before "
                    "calling early_reduction at or after FRA, and no "
                    "test in tests/ss/ asserts early_reduction(0)."
                ),
                "basis_derivation": basis_derivations["R8"],
            },
        },
        {
            "id": "R9_402w_delayed_retirement_credit",
            "statute": "42 USC 402(w)",
            "title": (
                "credit per month of delay at the cohort's annual "
                "rate, stopping at age 70"
            ),
            "code": code(("delayed_credit", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": factors["n_cases_invoking_402w_credit"],
            "pe_us_foundation_selector": (
                "the foundation cases whose committed our_factor is "
                "above 1, i.e. those that invoke the credit"
            ),
            "tests": [
                f"{TEST_BENEFITS_REL}::test_delayed_credit_pure_bundle",
                f"{TEST_BENEFITS_REL}::"
                "test_delayed_credit_rate_loads_from_pe_us",
            ],
            "e1": {
                "status": "policyengine_us_only",
                "basis": (
                    "not in the 240; the "
                    f"{factors['n_cases_invoking_402w_credit']} "
                    "credit cases of the foundation block are the only "
                    "independent execution"
                ),
            },
            "e2": {
                "status": "satisfied",
                "basis": (
                    "SSA's published 32 percent (48 months at an FRA of "
                    "66) and 24 percent (window truncated at age 70 "
                    "against an FRA of 67)"
                ),
            },
            "e3": {
                "status": "partial",
                "basis": (
                    "the 8 percent per year step is scored end to end "
                    "and the months_late <= 0 early return is asserted "
                    "directly; the 3 percent step for the earliest "
                    "cohorts is asserted as a parameter read only, and "
                    "the credited <= 0 branch (an FRA at or past age "
                    "70) is unreachable for every cohort in the "
                    "committed schedule and is unexercised."
                ),
                "basis_derivation": basis_derivations["R9"],
            },
        },
        {
            "id": "R10_416l_fra_schedule",
            "statute": "42 USC 416(l)",
            "title": "the full retirement age schedule by birth year",
            "code": code(("fra_months", params_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": foundation["n_cases"],
            "tests": [
                f"{TEST_BENEFITS_REL}::test_fra_schedule_matches_statute",
                f"{TEST_CLAIMING_REL}::"
                "test_fra_footnote_schedule_matches_oracle",
            ],
            "e1": {
                "status": "satisfied",
                "basis": (
                    "the schedule loads from policyengine-us and is "
                    "exercised through the foundation block's factor "
                    "agreement"
                ),
            },
            "e2": {
                "status": "satisfied",
                "basis": (
                    "65 / 66 / 67 by birth year asserted directly, and "
                    "Table 6.B5.1 footnote a's independently published "
                    "schedule reproduces it"
                ),
            },
            "e3": {
                "status": "all_branches_exercised",
                "basis": "all three FRA plateaus asserted",
            },
        },
        {
            "id": "R11_402q1_spousal_early_reduction",
            "statute": "42 USC 402(q)(1)",
            "title": (
                "25/36 of one percent per month for the first 36 "
                "months, 5/12 beyond (the spousal schedule)"
            ),
            "code": code(("spousal_early_reduction", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [
                "spouse_at_62_fra67",
                "spouse_at_62_fra66",
            ],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_AUX_REL}::test_spousal_early_reduction_brackets"
            ],
            "e1": {
                "status": "unsatisfiable_today",
                "basis": (
                    "policyengine-us carries no spousal computation, so "
                    "no second engine exists to disagree -- structural, "
                    "not incidental"
                ),
            },
            "e2": {
                "status": "satisfied",
                "basis": (
                    "SSA's published 32.5 percent of the worker PIA at "
                    "62 against an FRA of 67, and 35 percent against an "
                    "FRA of 66"
                ),
            },
            "e3": {
                "status": "partial",
                "basis": (
                    "months_early is exercised at 0, 36, 48 and 60 "
                    "only; both rate brackets are reached"
                ),
            },
        },
        {
            "id": "R12_402bc_402k3_spouse_benefit",
            "statute": "42 USC 402(b)(2)/(c)(2), 402(k)(3)(A)",
            "title": (
                "one-half of the worker's PIA, offset by the "
                "claimant's own PIA before the age reduction"
            ),
            "code": code(("spousal_benefit", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [
                "spouse_at_fra_half_pia",
                "spouse_dual_entitlement_excess",
            ],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_AUX_REL}::test_spousal_benefit_headline_shares",
                f"{TEST_AUX_REL}::test_spousal_dual_entitlement_offset",
            ],
            "e1": {
                "status": "unsatisfiable_today",
                "basis": "no second engine for the spousal path",
            },
            "e2": {
                "status": "partial",
                "basis": (
                    "the 50 percent share at FRA is published; the "
                    "excess case's expected value is the oracle's own "
                    "subtraction"
                ),
            },
            "e3": {
                "status": "partial",
                "basis": (
                    "the couple grid has no row in which BOTH spouses "
                    "draw an excess, so the symmetric dual-entitlement "
                    "case is unexercised"
                ),
            },
        },
        {
            "id": "R13_402q_survivor_reduction_ramp",
            "statute": "42 USC 402(q); SSA POMS RS 00615.302",
            "title": (
                "the widow(er) ramp spreading a 28.5 percent maximum "
                "reduction to the 71.5 percent floor at age 60"
            ),
            "code": code(("survivor_reduction", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": ["widow_at_60_floor", "widow_at_62_fra66"],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_AUX_REL}::test_survivor_reduction_ramp_and_floor",
                f"{TEST_AUX_REL}::test_widow_reduction_71_5_floor_at_60",
            ],
            "e1": {
                "status": "unsatisfiable_today",
                "basis": "no second engine for the survivor path",
            },
            "e2": {
                "status": "satisfied_with_a_constant_override",
                "basis": (
                    "the 71.5 percent floor at 60 is anchored on the "
                    "shipped default; the 81 percent at 62 case "
                    "reproduces SSA only by overriding "
                    "survivor_reduction_period_months to 72 in its own "
                    "inputs, because the shipped default is 84 and the "
                    "module carries no survivor-FRA schedule"
                ),
            },
            "e3": {
                "status": "partial",
                "basis": (
                    "the ramp, its midpoint and its clamp are asserted "
                    "in unit tests; the committed examples exercise two "
                    "spans"
                ),
            },
        },
        {
            "id": "R14_402ef_widow_riblim_drc_dual",
            "statute": ("42 USC 402(e)/(f), 402(e)(2)(D)/(k)(3)(A), 402(k)"),
            "title": (
                "widow base, the RIB-LIM cap, the delayed-credit "
                "pass-through and the dual-entitlement maximum"
            ),
            "code": code(("widow_benefit", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [
                "widow_at_fra_full_pia",
                "rib_lim_82_5_floor",
                "rib_lim_deceased_actual_higher",
                "drc_pass_through",
            ],
            "pe_us_foundation_cases": 0,
            "tests": [
                f"{TEST_AUX_REL}::test_widow_full_pia_and_dual_entitlement",
                f"{TEST_AUX_REL}::test_rib_lim_cases",
                f"{TEST_AUX_REL}::"
                "test_widow_inherits_credits_but_capped_at_deceased_amount",
            ],
            "e1": {
                "status": "unsatisfiable_today",
                "basis": "no second engine for the survivor path",
            },
            "e2": {
                "status": "partial",
                "basis": (
                    "100 percent at survivor FRA and the 82.5 percent "
                    "RIB-LIM floor are published; the higher-of branch "
                    "and the delayed-credit pass-through have expected "
                    "values that are the oracle's own PIA x factor "
                    "products"
                ),
            },
            "e3": {
                "status": "partial",
                "basis": (
                    "no committed worked example has own_pia > 0, so "
                    "the 402(k) dual-entitlement maximum is never "
                    "anchored to a published figure; the survivor grid "
                    "exercises it at one PIA pair"
                ),
            },
            "bundles_multiple_operations": True,
            "granularity_note": (
                "This rule bundles four statutory operations that could "
                "each earn or lose the status separately. The "
                "granularity is the packet's cut, not a measurement."
            ),
        },
        {
            "id": "R15_402e3_f4_remarriage_protection",
            "statute": "42 USC 402(e)(3)/(f)(4)",
            "title": (
                "remarriage at or after age 60 (50 if disabled) does "
                "not terminate a widow(er)'s benefit"
            ),
            "code": code(
                ("widow_benefit_survives_remarriage", benefits_spans)
            ),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": 0,
            "tests": [f"{TEST_AUX_REL}::test_remarriage_predicate"],
            "e1": {
                "status": "unsatisfiable_today",
                "basis": "no second engine for the survivor path",
            },
            "e2": {
                "status": "absent",
                "basis": (
                    "no committed artifact row exercises this rule at "
                    "all; the only evidence is a unit test asserting "
                    "the two statutory thresholds"
                ),
            },
            "e3": {
                "status": "unit_test_only",
                "basis": (
                    "both thresholds and both sides of each are "
                    "asserted, but no committed case set carries the "
                    "rule"
                ),
            },
        },
        {
            "id": "R16_age62_composition",
            "statute": "42 USC 416(l) composed with 402(q)",
            "title": "the monthly benefit for a claim at exactly age 62",
            "code": code(("age62_monthly_benefit", benefits_spans)),
            "cross_engine": none_of_240,
            "ssa_worked_examples": [],
            "pe_us_foundation_cases": factors["n_cases_at_claim_age_62"],
            "pe_us_foundation_selector": (
                "the foundation cases at claim age 62"
            ),
            "tests": [
                f"{TEST_BENEFITS_REL}::"
                "test_early_reduction_at_fra_67_claiming_62"
            ],
            "e1": {
                "status": "policyengine_us_only",
                "basis": (
                    "the composition is exercised through the "
                    "foundation block's claim-age-62 cases"
                ),
            },
            "e2": {
                "status": "satisfied",
                "basis": (
                    "700.0 at a PIA of 1000 for a worker born 1962, "
                    "SSA's published 70 percent at 62 against an FRA "
                    "of 67"
                ),
            },
            "e3": {
                "status": "partial_with_a_named_simplification",
                "basis": (
                    "the one-month eligibility subtlety for births on "
                    "the first two days of a month is documented in "
                    "the source and ignored; nothing exercises it"
                ),
            },
        },
    ]
    return rules


def _packet_verdicts() -> dict[str, str]:
    """The DRAFT partition the packet proposes, quoted for comparison."""
    return {
        "R1_415b1_wage_base_cap": "partial_no_external_anchor",
        "R2_415b3_nawi_indexation": "partial_no_external_anchor",
        "R3_415b2B_computation_year_count": "NOT_computes_exactly",
        "R4_415b_top_n_divide_and_floor": "partial_no_external_anchor",
        "R5_415a1A_pia_brackets": "partial_weak_anchor",
        "R6_415a1B_bend_points": "computes_exactly_two_years_only",
        "R7_415g_dime_floor": "computes_exactly",
        "R8_402q_worker_early_reduction": "computes_exactly_narrow_domain",
        "R9_402w_delayed_retirement_credit": (
            "computes_exactly_narrow_domain"
        ),
        "R10_416l_fra_schedule": "computes_exactly",
        "R11_402q1_spousal_early_reduction": ("partial_no_independent_engine"),
        "R12_402bc_402k3_spouse_benefit": "partial",
        "R13_402q_survivor_reduction_ramp": (
            "partial_constant_override_required"
        ),
        "R14_402ef_widow_riblim_drc_dual": "partial",
        "R15_402e3_f4_remarriage_protection": (
            "NOT_computes_exactly_unit_test_only"
        ),
        "R16_age62_composition": (
            "computes_exactly_with_named_simplification"
        ),
    }


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def build() -> dict[str, Any]:
    cross = _load(CROSS_ENGINE_REL)
    aux = _load(AUX_REL)

    doc_2023 = _load("data/external/ssa_claim_ages_2023supplement.json")

    benefits_spans = _spans(BENEFITS_REL)
    params_spans = _spans(PARAMS_REL)
    household_spans = _spans(HOUSEHOLD_REL)

    cross_inventory = _cross_engine_inventory(cross)
    cross_inventory["bend_points_provenance"] = _bend_points_provenance(cross)
    basis_derivations = {
        "R4": _r4_basis_derivation(),
        "R8": _r8_basis_derivation(),
        "R9": _r9_basis_derivation(doc_2023),
    }
    worked = _worked_example_inventory(aux)
    foundation = _foundation_inventory(aux)
    grids = _grid_inventory(aux)

    rules = _rule_inventory(
        benefits_spans,
        params_spans,
        cross_inventory,
        foundation,
        basis_derivations,
    )
    packet_verdicts = _packet_verdicts()
    for rule in rules:
        rule["packet_proposed_verdict"] = {
            "verdict": packet_verdicts[rule["id"]],
            "source": PACKET,
            "status": "proposal_not_ratified",
        }

    example_names = {row["name"] for row in worked["examples"]}
    test_names = {
        TEST_CROSS_ENGINE_REL: _test_names(TEST_CROSS_ENGINE_REL),
        TEST_AUX_REL: _test_names(TEST_AUX_REL),
        TEST_BENEFITS_REL: _test_names(TEST_BENEFITS_REL),
        TEST_CLAIMING_REL: _test_names(TEST_CLAIMING_REL),
    }

    zero_coverage = [
        {
            "id": rule["id"],
            "statute": rule["statute"],
            "reason": (
                "no committed cross-engine case and no committed SSA "
                "worked example exercises this rule"
            ),
            "only_evidence": rule["tests"],
        }
        for rule in rules
        if rule["cross_engine"]["n_cases"] == 0
        and not rule["ssa_worked_examples"]
        and not rule["pe_us_foundation_cases"]
    ]

    not_implemented = {
        name: _grep_absent(
            (
                COLA_SEARCH_ROOT
                if name == "cola_applied_to_pia"
                else PACKAGE_SEARCH_ROOT
            ),
            patterns,
        )
        for name, patterns in NOT_IMPLEMENTED_PATTERNS.items()
    }

    gates_citation = _gates_citation()

    return {
        "schema_version": SCHEMA_VERSION,
        "run": RUN,
        "reported_not_gated": True,
        "purpose": (
            "Per-rule coverage of the statutory benefit oracle. "
            "Changes no gate. For every statutory rule "
            "populace_dynamics.ss implements, records which committed "
            "cross-engine cases and which committed SSA worked "
            "examples exercise it, which rules have zero case "
            "coverage, and what the module does not implement at all. "
            "Quotes -- and does not adopt -- the DRAFT definition of "
            'the phrase "computes exactly".'
        ),
        "component": "statutory benefit oracle (#74 component SF)",
        "gate_status": {
            "gates_yaml_block": None,
            "gates_yaml_citation": gates_citation,
            "note": (
                "gates.yaml carries no gate_b2_pia_oracle. The phrase "
                '"computes exactly" occurs in gate_2\'s description '
                "only, where it awards a status no gate_2 cell gates. "
                "This artifact records that as read; it proposes no "
                "gate and amends nothing."
            ),
        },
        "no_engine_executed": {
            "statement": (
                "This build executed neither the Axiom rules engine nor "
                "a policyengine-us Simulation. Every cross-engine and "
                "policyengine-us number is quoted from the committed "
                "artifacts. The only things that execute either engine "
                "are the repo's existing tests in tests/ss/, which are "
                "named per rule below and are unchanged by this build."
            ),
            "engine_revision_quoted": cross["engine_revision"],
            "pe_us_revision_quoted": cross["pe_us_revision"],
        },
        "sources": {
            "oracle": [
                _pin(BENEFITS_REL),
                _pin(PARAMS_REL),
                _pin(SS_INIT_REL),
            ],
            "evidence_artifacts": [
                _pin(CROSS_ENGINE_REL),
                _pin(AUX_REL),
            ],
            "tests": [
                _pin(TEST_CROSS_ENGINE_REL),
                _pin(TEST_AUX_REL),
                _pin(TEST_BENEFITS_REL),
                _pin(TEST_CLAIMING_REL),
            ],
            "consumer": _pin(HOUSEHOLD_REL),
            "consumer_symbols": _consumer_symbols(household_spans),
            "code_reference_note": (
                "Every code span in rule_inventory is derived with ast "
                "from the pinned module, not typed, so a reproduction "
                "test re-derives it."
            ),
        },
        "frozen_scope": {
            "quote": (
                "Role: the ORACLE, not the rules engine. Net-new "
                "statute encoding lives in Axiom (rulespec-us "
                "us/statutes/42/415, 402, 416); this module is a "
                "frozen-scope Python reference implementation ... Do "
                "not extend this module's rule coverage; extend the "
                "Axiom encodings."
            ),
            "source": SS_INIT_REL,
            "consequence": (
                "A missing rule below is a SCOPE decision, not a "
                "defect, and is closed in Axiom rather than by growing "
                "this module."
            ),
        },
        "computes_exactly_definition_proposal": {
            "source": PACKET,
            "status": "proposal_not_ratified",
            "adopted_here": False,
            "gates_yaml_line_642": gates_citation["cited_line_text"],
            "gates_yaml_line_642_pinned_to_blob": gates_citation[
                "git_blob_sha1"
            ],
            "conditions": {
                "E1_independent_re_execution": (
                    "A separately implemented engine executes the rule "
                    "from the same pinned parameters and agrees on "
                    "every registered case within the committed "
                    "agreement bound. Precedent and bound already "
                    "committed: runs/pia_cross_engine_v1.json "
                    "agreement_tolerance_dollars: 0.005, i.e. to the "
                    'cent. "Exactly" means to the cent, not '
                    "bit-exact."
                ),
                "E2_external_anchor": (
                    "At least one registered case per rule whose "
                    "expected value is an SSA-published figure, not our "
                    "own arithmetic. A case whose expected is "
                    "recomputed from the same formula tests branch "
                    "selection, not correctness of the rule."
                ),
                "E3_exercised_branches_and_boundaries": (
                    "Every branch and every boundary of the rule as "
                    "written is hit by at least one registered case, "
                    "and the case set is committed cell-by-cell so a "
                    "referee re-derives rather than trusts."
                ),
            },
            "exclusions": {
                "X1_named_non_coverage": (
                    "Every statutory rule of the same title that the "
                    "module does not implement is listed by name and "
                    'citation, so "computes exactly" can never be '
                    'read as "computes everything".'
                ),
                "X2_named_constants": (
                    "Every quantity the statute makes a schedule but "
                    "the module makes a constant is listed with the "
                    "domain over which the constant is exact."
                ),
            },
            "why_e1_alone_is_insufficient": (
                "E1 alone is AGREEMENT, not correctness: two engines "
                "fed the same parameters can agree on the same "
                "mistake. E2 is what makes it a claim about the "
                "statute."
            ),
            "precision_disclosure": {
                "cross_engine_max_abs_diff_dollars": cross[
                    "max_abs_diff_dollars"
                ],
                "aux_worked_example_max_abs_deviation": aux[
                    "ssa_worked_examples"
                ]["max_abs_deviation"],
                "pe_us_foundation_max_pia_abs_deviation": foundation[
                    "max_pia_abs_deviation"
                ],
                "pe_us_foundation_max_factor_abs_deviation": foundation[
                    "max_factor_abs_deviation"
                ],
            },
        },
        "evidence_inventory": {
            "cross_engine": cross_inventory,
            "ssa_worked_examples": worked,
            "pe_us_pia_foundation": foundation,
            "grids": grids,
        },
        "status_provenance": {
            "statement": (
                "The E1 / E2 / E3 status labels are the builder's "
                "READING of the derived evidence, typed as strings in "
                "_rule_inventory; the evidence fields beside them "
                "(case counts, ast code spans, bracket occupancy, the "
                "dime-floor sweep, the factor split, the not-implemented "
                "searches and the basis_derivation blocks of R4, R8 and "
                "R9) are derived from committed bytes and re-derived by "
                "tests. A status label is pinned only by the "
                "byte-reproduction test; a later editor can change one by "
                "editing a string and rebuilding, which is why the "
                "statuses below award nothing and the packet's proposed "
                "verdicts are quoted, not adopted (referee A, F8; "
                "referee B, D5)."
            ),
            "rules_with_a_derived_e3_basis": sorted(basis_derivations),
            "every_derived_basis_holds": all(
                block["claim_holds"] for block in basis_derivations.values()
            ),
        },
        "rule_inventory": rules,
        "n_rules": len(rules),
        "zero_coverage_rules": zero_coverage,
        "n_zero_coverage_rules": len(zero_coverage),
        "coverage_summary": {
            "rules_with_cross_engine_cases": [
                rule["id"]
                for rule in rules
                if rule["cross_engine"]["n_cases"] > 0
            ],
            "rules_with_no_cross_engine_case": [
                rule["id"]
                for rule in rules
                if rule["cross_engine"]["n_cases"] == 0
            ],
            "rules_with_an_ssa_worked_example": [
                rule["id"] for rule in rules if rule["ssa_worked_examples"]
            ],
            "rules_with_no_ssa_worked_example": [
                rule["id"] for rule in rules if not rule["ssa_worked_examples"]
            ],
            "every_named_worked_example_exists": all(
                name in example_names
                for rule in rules
                for name in rule["ssa_worked_examples"]
            ),
            "every_named_test_module_is_pinned": all(
                reference.split("::")[0] in test_names
                for rule in rules
                for reference in rule["tests"]
            ),
            "every_named_test_exists": all(
                reference.split("::")[-1]
                in test_names[reference.split("::")[0]]
                for rule in rules
                for reference in rule["tests"]
            ),
        },
        "named_constants": {
            "note": (
                "X2 of the proposed definition: quantities the statute "
                "makes a SCHEDULE and the module makes a CONSTANT, with "
                "the domain over which each is exact."
            ),
            "computation_years": {
                "value": COMPUTATION_YEARS,
                "code": benefits_spans["_COMPUTATION_YEARS"],
                "statute": "42 USC 415(b)(2)(B)",
                "exact_domain": (
                    "retirement workers attaining age 62 in 1991 or "
                    "later, for whom elapsed years minus five dropout "
                    "years is 35"
                ),
                "wrong_outside": (
                    "survivor and disability PIAs, where an early death "
                    "or a disability freeze shortens the elapsed count"
                ),
                "live_caller_outside_the_domain": {
                    "symbol": "widow_benefit",
                    "code": benefits_spans["widow_benefit"],
                    "note": (
                        "widow_benefit takes deceased_pia from the "
                        "caller; a pipeline that computes a deceased "
                        "worker's PIA through aime() gets a 35-year "
                        "divisor. No committed artifact scores that "
                        "path."
                    ),
                },
            },
            "survivor_reduction_period_months": {
                "value": 84,
                "code": params_spans["survivor_reduction_period_months"],
                "statute": "42 USC 416(l) as applied to survivors",
                "exact_domain": (
                    "survivor cohorts born 1962 or later (survivor FRA "
                    "67, an 84-month span)"
                ),
                "wrong_outside": (
                    "survivor FRA 65 (60-month span) and 66 (72-month "
                    "span) cohorts; the shipped default carries no "
                    "survivor-FRA schedule"
                ),
                "evidence": (
                    "the widow_at_62_fra66 worked example reproduces "
                    "SSA only by overriding the default to 72 in its "
                    "own inputs"
                ),
            },
            "one_month_eligibility_subtlety": {
                "code": benefits_spans["age62_monthly_benefit"],
                "content": (
                    "births on the first two days of a month are "
                    "ignored; at most one month's reduction factor. "
                    "Documented in the source and restated here so it "
                    "sits inside the coverage record, not only in a "
                    "docstring."
                ),
            },
        },
        "not_implemented": {
            "note": (
                "X1 of the proposed definition. Each entry records the "
                "search root, the patterns, the number of Python files "
                "searched and the (empty) hit list, so the absence is "
                "re-derivable rather than asserted."
            ),
            "searches": not_implemented,
            "all_absent": all(
                block["absent"] for block in not_implemented.values()
            ),
            "additional_absences_from_a_full_read_of_the_module": [
                "child's and parent's benefits, and the child-in-care "
                "spouse's benefit",
                "the disability PIA (no freeze, no alternate "
                "computation years)",
                "recomputation for post-entitlement earnings",
            ],
            "family_maximum_bites_here": {
                "symbols": ["spousal_benefit", "widow_benefit"],
                "code": [
                    benefits_spans["spousal_benefit"],
                    benefits_spans["widow_benefit"],
                ],
                "consumer": HOUSEHOLD_REL,
                "note": (
                    "Both auxiliary functions return uncapped amounts "
                    "and household.CoupleBenefit.total sums both own "
                    "benefits plus both excess spousal amounts with no "
                    "cap. The family maximum binds precisely where "
                    "auxiliary benefits stack, and no committed case "
                    "stacks enough for it to bind."
                ),
                "consumer_symbols": _consumer_symbols(household_spans),
                "search_patterns_note": (
                    "the family-maximum absence is re-derivable only "
                    "against the literal patterns in "
                    "not_implemented.searches.family_maximum.patterns; "
                    "v2 widened them (maximum_family_benefit, fam_max)"
                ),
            },
        },
        "known_gaps": [
            {
                "id": "r3_computation_year_count_is_degenerate",
                "statement": (
                    "The oracle hard-codes 35 and the engine derives n, "
                    "but the committed artifact's own note records "
                    "elapsed - 5 = 35 for both cohorts, so no committed "
                    "case distinguishes them."
                ),
            },
            {
                "id": "r4_zero_pad_branch_unexercised",
                "statement": (
                    "The short-history zero-pad branch of aime() is "
                    "reached by no committed cross-engine case and by "
                    "no test in tests/ss/: every committed worker "
                    "history has 41 entries, so the top-n slice always "
                    "yields 35 values and the pad is a no-op."
                ),
            },
            {
                "id": "r8_r16_absent_from_the_240",
                "statement": (
                    "The cross-engine rows carry aime and pia only, so "
                    "every rule from 402(q) onward rests on the 40-case "
                    "policyengine-us foundation block and the committed "
                    "worked examples."
                ),
            },
            {
                "id": "r11_r15_no_second_engine",
                "statement": (
                    "policyengine-us has no spousal or survivor "
                    "computation, so E1 is unsatisfiable for the "
                    "auxiliary rules today. What would satisfy it is "
                    "named in ss/__init__.py: the Axiom rulespec-us "
                    "us/statutes/42/402 encodings."
                ),
            },
            {
                "id": "r12_r14_grid_thinness",
                "statement": (
                    "The couple grid has no row with both spouses "
                    "drawing an excess; the survivor grid sits at a "
                    "single PIA pair; and no worked example has own_pia "
                    "above zero, so the dual-entitlement maximum is "
                    "never anchored to a published figure."
                ),
            },
        ],
        "packet_reconciliation": {
            "packet": PACKET,
            "purpose": (
                "Where this build's derivation differs from the "
                "coverage claim the DRAFT packet states, the difference "
                "is recorded here rather than silently adopted."
            ),
            "differences": [
                {
                    "field": "R4 -- the 415(b) short-history zero pad",
                    "packet_states": (
                        "E3 satisfied: 'short-history zero-pad branch "
                        "(:116) hit by all_zeros / zero_spell'"
                    ),
                    "derived_here": (
                        "the branch is hit by NO committed case: every "
                        "worker history has 41 entries, and the "
                        "all_zeros and zero_spell shapes carry zero "
                        "EARNINGS rather than missing YEARS, so the pad "
                        "is always a no-op"
                    ),
                    "consequence": (
                        "R4's E3 status is branch_unexercised here, not "
                        "satisfied"
                    ),
                },
                {
                    "field": ("R1 -- the count of wage-base-clipped workers"),
                    "packet_states": (
                        "'clipped_always + rand_clipped_always = 25 "
                        "workers'"
                    ),
                    "derived_here": (
                        "clipped_always = "
                        f"{cross_inventory['shape_counts'].get('clipped_always', 0)}"
                        " and rand_clipped_always = "
                        f"{cross_inventory['shape_counts'].get('rand_clipped_always', 0)}"
                        ", so "
                        f"{cross_inventory['shape_counts'].get('clipped_always', 0) + cross_inventory['shape_counts'].get('rand_clipped_always', 0)}"
                        " workers carry a clipping shape label"
                    ),
                    "consequence": (
                        "a count correction only; it changes no E1/E2/E3 "
                        "status, and the exact number of cases in which "
                        "the cap BINDS remains undeterminable from the "
                        "committed bytes"
                    ),
                },
                {
                    "field": (
                        "the household consumer that stacks auxiliary "
                        "benefits"
                    ),
                    "packet_states": (
                        "household.couple_benefits (household.py:143-149)"
                    ),
                    "derived_here": (
                        "the summation is the CoupleBenefit.total "
                        "property (class CoupleBenefit, singular); the "
                        "module's function is couple_benefit. Both "
                        "symbols are derived by ast in "
                        "sources.consumer_symbols."
                    ),
                    "consequence": (
                        "a naming correction; the substance -- that "
                        "both own benefits and both excess spousal "
                        "amounts are summed with no family maximum -- "
                        "holds as read"
                    ),
                    "v1_defect": (
                        "the v1 artifact named the class CoupleBenefits "
                        "(plural), a symbol that exists nowhere in src/ "
                        "or tests/ (referee A, F9-4; referee B, D4 / "
                        "F1); corrected in v2 and pinned by ast"
                    ),
                },
            ],
        },
        "does_not_establish": [
            "any per-rule status: the E1/E2/E3 fields record what the "
            "committed evidence reaches, and the packet's proposed "
            "verdicts are quoted for comparison, not adopted",
            'that the proposed definition of "computes exactly" is '
            "the right one: no referee round has run",
            "any statement about the Axiom engine or policyengine-us "
            "beyond what the committed artifacts record; neither was "
            "executed here",
            "that the rule granularity is correct: sixteen rules is the "
            "packet's cut, and R12 and R14 each bundle several "
            "statutory operations",
            "that any E1 status has been re-executed in this ceremony: "
            "the three engine-backed tests in tests/ss/ skip on a host "
            "without the Axiom wheel or a policyengine-us Python, and "
            "every E1 status rests on the committed cross-engine artifact "
            "as built on its recorded date",
            "the sequencing of the lock PR: the gates.yaml citation is "
            "blob-pinned and survives the gate commit, but the two 'gate "
            "name absent from gates.yaml' tests read the live file by "
            "design and fail the moment gate_b2_pia_oracle or "
            "gate_b2_claiming lands; the commit that inserts either "
            "block must retire those assertions or supersede this "
            "artifact with a v2 in the same PR",
            "that the typed bend-point pairs are SSA determinations: the "
            "2026 pair has an SSA-anchor test, the 2020 pair is pinned "
            "only to the committed cross-engine rows it reproduces",
        ],
        "build": {
            "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "built_by": "scripts/build_pia_rule_coverage.py",
        },
    }


def main() -> None:
    artifact = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2) + "\n")
    summary = artifact["coverage_summary"]
    print(
        f"wrote {OUT_PATH}\n"
        f"  rules: {artifact['n_rules']}\n"
        f"  with a cross-engine case: "
        f"{len(summary['rules_with_cross_engine_cases'])}; "
        f"with an SSA worked example: "
        f"{len(summary['rules_with_an_ssa_worked_example'])}\n"
        f"  zero case coverage: {artifact['n_zero_coverage_rules']} "
        f"({', '.join(r['id'] for r in artifact['zero_coverage_rules'])})\n"
        f"  named worked examples all exist: "
        f"{summary['every_named_worked_example_exists']}; "
        f"named tests all exist: {summary['every_named_test_exists']}\n"
        f"  not-implemented searches all absent: "
        f"{artifact['not_implemented']['all_absent']}"
    )


if __name__ == "__main__":
    main()
