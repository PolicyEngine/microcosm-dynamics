"""Count-only input preparation for a2-ratified-1 §16.7.

Compose the inherited A3 transformations, preserving projection inputs,
without invoking A3/A5 diagnostics. Those diagnostics compute forbidden
weight sums (cohorts/psid2010.py:1342–1346,2166 and
cola_track_a/opening.py:599). No protected function is modified.
"""

from __future__ import annotations

import pandas as pd

from populace_dynamics.cohorts import psid2010 as a3
from populace_dynamics.cola_track_a import opening
from populace_dynamics.cola_track_a.config import (
    INVENTED_COHORT_LABEL,
    TRACK_A_LABELS,
    TrackAConfig,
)


def build_structural_source(raw, spec=None):
    """A3's exact preparation order, omitting only diagnostic summaries.

    The orchestration follows cohorts/psid2010.py:2097–2189. Its Social
    Security helpers select existing observed amounts and receipt flags
    (:1638–1747); they never calculate a PIA or a scenario benefit.
    """
    spec = spec or a3.Psid2010CohortSpec(anchor_wave=2011)
    if spec.anchor_wave != 2011 or int(raw.anchor_wave) != 2011:
        raise ValueError("structural protocol permits only the 2011 wave")
    a3._validate_inputs(raw)
    input_provenance = a3._input_provenance(raw)
    wave, start = spec.anchor_wave, spec.start_year
    anchor = raw.anchor
    universe = anchor[a3._presence_mask(anchor, spec.presence)].copy()
    universe_ids = set(int(pid) for pid in universe["person_id"])
    seed = pd.DataFrame(
        {
            "person_id": universe["person_id"].astype("int64"),
            "year": start,
            "anchor_wave": wave,
            "age": universe["age"].astype("int64"),
        }
    )
    history, earnings = raw.marriage_history, raw.observed_earnings
    records = a3.career.derive_birth_years(
        history[history["person_id"].isin(universe_ids)],
        earnings[earnings["person_id"].isin(universe_ids)],
        seed_coordinates=seed,
        required_person_ids=universe_ids,
    )
    births = {record.person_id: record for record in records}
    if set(births) != universe_ids:
        raise AssertionError("birth dispositions are not universe-total")
    classified = a3._dispositions(
        universe, births, raw.death_records.set_index("person_id")["sex"], spec
    )
    dispositions = classified[
        ["person_id", "weight", "disposition"]
    ].reset_index(drop=True)
    members = classified[classified["disposition"] == "member"].sort_values(
        "person_id"
    )
    persons = a3._base_persons(members, spec)
    a3._attach_death(persons, raw.death_records, wave)
    a3._attach_marital(persons, raw, births, universe_ids, spec)
    a3._attach_coresident_partner(persons, anchor, wave)
    a3._attach_m4(persons, raw.disability_status, spec)
    social_security = a3._social_security_rows(
        persons, raw.head_spouse_ss, raw.individual_ss, spec
    )
    a3._attach_social_security(persons, social_security, start)
    a3._attach_opening_status(persons, spec)
    a3._attach_opening_claim(persons, raw, spec)
    careers = a3._careers(persons, earnings, start)
    built = a3.Psid2010Cohort(
        persons=persons,
        careers=careers,
        social_security=social_security,
        dispositions=dispositions,
        spec=spec,
        diagnostics={},
    )
    object.__setattr__(
        built,
        "provenance",
        a3.ReadOnlyProvenance(
            {
                **input_provenance,
                "anchor_wave": wave,
                "start_year": start,
                "set_by": "populace_dynamics.track_a_v2.structural_inputs.build_structural_source",
                "content_sha256": a3.cohort_content_sha256(built),
                "content_basis": a3._CONTENT_BASIS,
            }
        ),
    )
    return built


def _source_provenance(source, data_provenance):
    """Retain opening.py:438–508's checks without diagnostic regeneration."""
    recorded = dict(source.provenance)
    expected_kind = {"invented": a3.INVENTED, "registered_real": a3.PSID_FILES}
    if (
        data_provenance not in expected_kind
        or recorded.get("kind") != expected_kind[data_provenance]
    ):
        raise ValueError("structural source provenance contradicts its label")
    if recorded.get("content_sha256") != a3.cohort_content_sha256(source):
        raise ValueError("structural source changed after preparation")
    if data_provenance == "invented":
        from populace_dynamics.cola_track_a import invented

        seed = recorded.get("seed")
        if not invented._is_seed(seed):
            raise ValueError("invented structural source has no valid seed")
        raw = invented.invented_psid2010_inputs(
            seed=seed,
            anchor_wave=source.anchor_wave,
            claiming_pmf=invented._any_year_claiming_pmf(
                source.spec.claim_table_max_year
            ),
        )
        if a3.input_frames_sha256(raw) != recorded.get("input_frames_sha256"):
            raise ValueError("invented structural source frame digest differs")
        rebuilt = build_structural_source(raw, source.spec)
        if a3.cohort_data_sha256(rebuilt) != a3.cohort_data_sha256(source):
            raise ValueError(
                "invented structural source differs from generator"
            )
    return a3.ReadOnlyProvenance(recorded)


def prepare_structural_cohort(raw, *, data_provenance, config=None):
    """Preserve opening records and states without benefit or weight totals.

    §16.7 forbids diagnostics even when discarded. Therefore compose
    opening.py:555–584's input transformations directly, then construct
    the same cohort with empty diagnostics. The opening-record helper
    only copies an observed amount (:364–374), never a derived benefit.
    """
    config = config or TrackAConfig(rows=tuple(f"R{i}" for i in range(6)))
    source = build_structural_source(raw)
    provenance = _source_provenance(source, data_provenance)
    columns = opening._opening_columns(source)
    if set(opening._STATIC_COLUMNS) - set(columns):
        raise ValueError("structural A3 persons lack opening columns")
    persons = (
        columns[list(opening._STATIC_COLUMNS)]
        .sort_values("person_id")
        .reset_index(drop=True)
        .copy()
    )
    if persons["person_id"].duplicated().any():
        raise ValueError("structural persons contain duplicate person_id")
    if (
        persons["age_opening"] != source.start_year - persons["birth_year"]
    ).any():
        raise ValueError("structural opening ages disagree with birth years")
    records = {}
    receipt = persons["ss_receipt_opening"].fillna(False).astype(bool)
    for row in persons[receipt].itertuples(index=False):
        record, _ = opening._opening_record(row, config, source.start_year)
        if record is not None:
            records[record.person_id] = record
    labels = (
        (INVENTED_COHORT_LABEL, *TRACK_A_LABELS[1:])
        if data_provenance == "invented"
        else TRACK_A_LABELS
    )
    cohort = opening.TrackACohort(
        persons=persons,
        careers=opening._careers(source),
        initial_slice=opening._initial_slice(persons, source.start_year),
        opening=records,
        data_provenance=data_provenance,
        labels=labels,
        diagnostics={},
        anchor_wave=source.anchor_wave,
        source_provenance=provenance,
    )
    object.__setattr__(cohort, "seal", opening.track_a_cohort_sha256(cohort))
    return cohort
