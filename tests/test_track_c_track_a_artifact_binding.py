"""Track C step 1's binding to the committed Track A artifact, by key.

Reads the cohort diagnostics recorded in the committed
``runs/replication_urban2010_cola_v1.json`` (Registration 13's artifact)
and the diagnostics the current ``cola_track_a.opening`` code produces for
INVENTED people (``cola_track_a.invented``; no PSID data).  The per-rule
breakdowns below are INVENTED splits of the recorded totals.

Regression: #454 added ``opening_stock_entitlement_clamped_by_clock_rule``
to the cohort diagnostics after the artifact was committed, and
``scripts/track_c_aime_agreement.py`` compared the whole diagnostics dict,
so every real run stopped before any engine call.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path

from populace_dynamics.cohorts import psid2010
from populace_dynamics.cola_track_a import (
    TrackAConfig,
    invented,
    prepare_track_a_cohort,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "runs" / "replication_urban2010_cola_v1.json"
ADDITIVE_KEY = "opening_stock_entitlement_clamped_by_clock_rule"
TOTAL_KEY = "opening_stock_entitlement_clamped"
CATEGORIES_KEY = "opening_stock_clock_rules"


def _load_script():
    path = ROOT / "scripts" / "track_c_aime_agreement.py"
    spec = importlib.util.spec_from_file_location(
        "track_c_aime_artifact_binding", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Dataclasses resolve their module through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tc = _load_script()


@lru_cache(maxsize=1)
def _code_diagnostics() -> dict:
    """The diagnostics the current code produces (INVENTED people)."""
    cohort = prepare_track_a_cohort(
        psid2010.build_psid2010_cohort(
            invented.invented_psid2010_inputs(seed=7)
        ),
        data_provenance="invented",
        config=TrackAConfig(),
    )
    return dict(cohort.diagnostics)


def _recorded(wave: str = "2011") -> tuple[dict, dict, dict]:
    artifact = json.loads(ARTIFACT.read_text())
    recorded = dict(artifact["cohorts"][wave])
    source = recorded.pop("source_provenance")
    return artifact, recorded, source


def test_the_artifact_records_a_subset_of_the_code_s_diagnostics():
    fresh = set(_code_diagnostics())
    for wave in ("2011", "2009"):
        _, recorded, _ = _recorded(wave)
        # Every recorded key must still be produced, or Track C refuses.
        assert set(recorded) <= fresh, set(recorded) - fresh
        # The key #454 added is produced but not recorded.
        assert ADDITIVE_KEY in fresh - set(recorded)
        assert TOTAL_KEY in recorded


def test_the_reviewed_additive_diagnostics_are_exactly_what_the_code_adds():
    # A diagnostic the code starts producing after this test was written
    # fails here, and Track C refuses to bind until it is reviewed and
    # listed in KNOWN_ADDITIVE_DIAGNOSTICS.
    produced = _code_diagnostics()
    for wave in ("2011", "2009"):
        _, recorded, _ = _recorded(wave)
        assert set(produced) - set(recorded) == set(
            tc.KNOWN_ADDITIVE_DIAGNOSTICS
        )
        for known in tc.KNOWN_ADDITIVE_DIAGNOSTICS.values():
            assert known["total"] in recorded
            assert known["categories"] in recorded
    # What each listing claims holds for the code's own (INVENTED)
    # diagnostics: the breakdown sums to its total and fits its categories.
    for key, known in tc.KNOWN_ADDITIVE_DIAGNOSTICS.items():
        breakdown = produced[key]
        categories = produced[known["categories"]]
        assert sum(breakdown.values()) == produced[known["total"]]
        assert all(
            0 <= count <= categories[name] for name, count in breakdown.items()
        )


def test_the_recorded_2011_cohort_binds_with_the_added_breakdown():
    artifact, recorded, source = _recorded()
    total = recorded[TOTAL_KEY]
    assert isinstance(total, int) and total > 0
    # INVENTED split of the recorded total over two clock rules.
    split = {"linked_worker_birth_plus_62": 1, "own_birth_plus_62": total - 1}
    fresh = {**recorded, ADDITIVE_KEY: split}
    # The whole-dict comparison the script used to make fails.
    assert tc._json_normal(recorded) != tc._json_normal(fresh)
    kwargs = dict(
        anchor_wave=2011,
        source_provenance=source,
        parameters_revision=artifact["ssa_parameters_revision"],
    )
    binding = tc.track_a_artifact_binding(
        artifact, diagnostics=fresh, **kwargs
    )
    assert all(binding["checks"].values()), binding["checks"]
    assert binding["recorded_diagnostic_keys"] == sorted(recorded)
    assert binding["additive_diagnostic_keys"] == {ADDITIVE_KEY: split}
    assert binding["additive_breakdowns"][ADDITIVE_KEY] == {
        "added_by": "bfe9fa3e",
        "total_key": TOTAL_KEY,
        "recorded_total": total,
        "sum": total,
        "sums_to_recorded_total": True,
        "categories_key": CATEGORIES_KEY,
        "within_recorded_categories": True,
    }
    # An INVENTED split one short of the recorded total is refused.
    one_short = {
        "linked_worker_birth_plus_62": 1,
        "own_birth_plus_62": total - 2,
    }
    short = tc.track_a_artifact_binding(
        artifact, diagnostics={**recorded, ADDITIVE_KEY: one_short}, **kwargs
    )
    assert not short["checks"]["additive_breakdowns_sum_to_recorded_totals"]
    # An INVENTED split that sums to the total but puts it all under the
    # least-counted recorded clock rule, which the artifact counts fewer
    # times than that, is refused.
    rules = recorded[CATEGORIES_KEY]
    fewest = min(rules, key=rules.get)
    assert rules[fewest] < total
    crowded = tc.track_a_artifact_binding(
        artifact,
        diagnostics={**recorded, ADDITIVE_KEY: {fewest: total}},
        **kwargs,
    )
    assert crowded["checks"]["additive_breakdowns_sum_to_recorded_totals"]
    assert not crowded["checks"][
        "additive_breakdowns_within_recorded_categories"
    ]
    # A diagnostic the code does not list is refused.
    unknown = tc.track_a_artifact_binding(
        artifact,
        diagnostics={**fresh, "invented_new_counter": 7},
        **kwargs,
    )
    assert not unknown["checks"]["additive_diagnostic_keys_known"]
    # Dropping a recorded key is refused.
    dropped = {k: v for k, v in fresh.items() if k != TOTAL_KEY}
    missing = tc.track_a_artifact_binding(
        artifact, diagnostics=dropped, **kwargs
    )
    assert missing["recorded_keys_missing"] == [TOTAL_KEY]
    assert not missing["checks"]["cohort_diagnostics_equal_on_recorded_keys"]
