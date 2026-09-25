"""The dry run's C0 membership text, from each row's record (INVENTED).

``scripts/fra68_dry_run.py`` words the C0 membership check and the
membership table from each row's ``membership_differences`` record
(E1 sections 7, 12 and 16; ``e1-ratified-2``).  A row whose rows A7
refused to normalize carries an unclassified record (``classified``
false, no counts; the runner then records A7's refusal as the row
status).  The text must name such a row, not fail on it.  Every record
and counter below is INVENTED; no run is made and no data is read.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from populace_dynamics.fra68_track.benefits import (
    SPOUSE_EXCESS_WITHHELD,
    WITHHELD_EXCESS,
    WITHHELD_EXCESS_NO_REFORM_BENEFIT,
)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fra68_dry_run.py"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("_fra68_dry_run", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(*, differ: int, named: int, allowed: bool) -> dict:
    return {
        "classified": True,
        "n_rows_differ": differ,
        "n_rows_not_explained": differ - named,
        "not_explained_allowed": allowed,
        "named_mechanisms": {SPOUSE_EXCESS_WITHHELD: {"n_rows": named}},
    }


def _result(records: dict[str, dict], counters=None) -> dict:
    return {
        "rows": {
            row_id: {
                "membership_differences": record,
                "benefit_counters": dict(counters or {}),
            }
            for row_id, record in records.items()
        }
    }


def test_coinciding_memberships_are_worded_as_such(script):
    result = _result(
        {
            "F0": _record(differ=0, named=0, allowed=False),
            "F3": _record(differ=5, named=0, allowed=True),
        }
    )
    line = script._c0_membership_line(result)
    assert "coincided in every row" in line
    assert "not classified" not in line
    table = "\n".join(script._membership_table(result))
    assert "| F0 | 0 | 0 | 0 | 0 | 0 |" in table
    assert "| F3 | 5 | 0 | 5 (allowed) | 0 | 0 |" in table


def test_named_c0_rows_are_counted_row_by_row(script):
    counters = {WITHHELD_EXCESS: 3, WITHHELD_EXCESS_NO_REFORM_BENEFIT: 2}
    result = _result(
        {
            "F0": _record(differ=2, named=2, allowed=False),
            "F6": _record(differ=0, named=0, allowed=False),
        },
        counters,
    )
    line = script._c0_membership_line(result)
    assert "differed in F0 2, F6 0 person-draw rows" in line
    assert f"`{SPOUSE_EXCESS_WITHHELD}`" in line
    table = "\n".join(script._membership_table(result))
    assert "| F0 | 2 | 2 | 0 | 3 | 2 |" in table


def test_an_unclassified_row_is_named_not_a_failure(script):
    # Regression: the text read "not_explained_allowed" and the counts of
    # every record, so a row whose rows A7 refused (an unclassified
    # record) raised KeyError after the run had finished.
    unclassified = {
        "classified": False,
        "reason": "A7 refused to normalize the rows (INVENTED reason)",
    }
    result = _result(
        {
            "F0": _record(differ=0, named=0, allowed=False),
            "F1": unclassified,
        },
        {WITHHELD_EXCESS: 1},
    )
    line = script._c0_membership_line(result)
    assert "coincided in every row" in line
    assert "not classified, because A7 refused their rows: F1" in line
    table = "\n".join(script._membership_table(result))
    assert "| F1 | not classified (A7 refused the rows) | - | - | 1 | 0 |" in (
        table
    )
