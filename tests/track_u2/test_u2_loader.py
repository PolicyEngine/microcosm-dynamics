"""The registered U2 loader's stages 2 and 3 on an invented staged
directory (section 14; review finding 6 of the u2m2 review).

INVENTED DATA - NOT A COMPARISON.  An unfrozen load without Max's
recorded authorization refuses before any PSID path is resolved, and
since amendment 1c's registry commit stage 1 passes at the committed
registries, opening no PSID file (``test_u2_mappings.py``).  To execute
the rest of the loader before any real record is read, this module
stages the invented population as PSID-shaped fixed-width files -- one
family file and setup per support wave, written at the registry layouts,
and an individual file and setup -- in a temporary directory and runs
:func:`loader.load_u2_inputs` against it, an unfrozen load with an
invented authorization record (:data:`TEST_AUTHORIZATION`, naming no
real decision), with up to five patches, each named where it is applied:

* ``sources.blockers`` returns no blocker, so stage 1 and the registry
  gate pass whatever the committed registries hold (the registry's own
  routes, not the declared ones, are applied);
* ``loader.check_source_hashes`` returns nothing, because the registries
  cite the real PSID setup files and codebooks, which are not staged
  here (the rehash itself is tested in ``test_u2_mappings.py``);
* the inherited marriage-history and earnings readers return the
  invented frames;
* for a frozen load, ``loader.read_preregistration_evidence`` returns the
  invented evidence record the load is given, standing in for the
  committed record (none is committed yet; a frozen load refuses any
  other record, ``test_a_frozen_load_needs_the_committed_record``).

An audit hook refuses any open under the PSID directory -- the default
one and the one under the account's real home, which differ when HOME is
overridden -- for the duration of each load.  Everything else -- path
resolution, the setup cross-checks, the fixed-width reads, the file
hashes and the seal -- is the code a registered run executes.
"""

from __future__ import annotations

import copy
import hashlib
import math
import os
import pwd
import sys
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import family, marriage, panels, psid
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    invented,
    loader,
    parameters,
    rows,
    runner,
    sources,
)

POINTER = (
    "https://github.com/PolicyEngine/microcosm-dynamics/issues/42"
    "#issuecomment-1"
)
_NA_BIRTH_YEAR = 9999
_SEX_CODES = {"male": 1, "female": 2, "na": 9}

_GUARD = {"active": False, "opened": []}
#: The default PSID directory, and the same directory under the
#: account's real home (``~`` expands to an overridden HOME).
_PSID_ROOTS = (
    str(psid._DEFAULT_DATA_DIR),
    str(
        Path(pwd.getpwuid(os.getuid()).pw_dir)
        / psid._DEFAULT_DATA_DIR.relative_to(Path.home())
    ),
)


def _psid_guard(event, args):
    if not _GUARD["active"] or event not in (
        "open",
        "os.listdir",
        "os.scandir",
    ):
        return
    if not args or isinstance(args[0], int):
        return
    path = os.fsdecode(args[0])
    if path.startswith(_PSID_ROOTS):
        _GUARD["opened"].append(path)
        raise PermissionError(f"the test refuses a PSID read: {path}")


sys.addaudithook(_psid_guard)


def _setup(specs) -> str:
    """An invented SPSS setup whose DATA LIST holds ``specs``."""

    lines = "\n".join(
        f"   {spec.variable} {spec.start} - {spec.end}"
        for spec in sorted(specs, key=lambda spec: spec.start)
    )
    return f"DATA LIST FILE = INVENTED /\n{lines}\n.\n"


def _individual_lines(inputs: cohort.U2Inputs, specs) -> list[str]:
    """One invented individual-file record per person at the registry
    layouts (weights rounded to the documented whole-number field)."""

    values: dict[str, pd.Series] = {}
    person = inputs.persons.set_index("person_id")
    ids = person.index.to_numpy(dtype=np.int64)
    values["common.person_family_id"] = pd.Series(ids // 1000, index=ids)
    values["common.person_number"] = pd.Series(ids % 1000, index=ids)
    values["common.sex"] = person["sex"].map(_SEX_CODES)
    design = inputs.design.set_index("person_id")
    values["common.stratum"] = design["stratum"]
    values["common.cluster"] = design["cluster"]
    for wave, anchor in inputs.anchors.items():
        frame = anchor.set_index("person_id")
        for concept in loader.ANCHOR_CONCEPTS:
            column = frame[concept]
            if concept == "reported_birth_year":
                column = column.fillna(_NA_BIRTH_YEAR).astype("int64")
            elif concept == "weight":
                column = column.round().astype("int64")
            values[f"{wave}.{concept}"] = column
    width = max(spec.end for spec in specs)
    out = []
    for pid in ids:
        chars = [" "] * width
        for spec in specs:
            text = str(int(values[spec.concept].loc[pid]))
            assert len(text) <= spec.width, (spec.concept, text)
            chars[spec.start - 1 : spec.end] = list(text.rjust(spec.width))
        out.append("".join(chars))
    return out


def _stage(root, inputs: cohort.U2Inputs, registries) -> set[str]:
    """Write the invented PSID-shaped files under ``root``."""

    staged = set()
    declared = sources.SourceGate(sources.INVENTED_DECLARED, registries)
    for wave in sources.SUPPORT_WAVES:
        records = invented.invented_fixed_width_records(inputs, wave, declared)
        directory = root / "family" / str(wave)
        directory.mkdir(parents=True)
        (directory / f"FAM{wave}ER.sps").write_text(_setup(records["specs"]))
        (directory / f"FAM{wave}ER.txt").write_text(
            "\n".join(records["lines"]) + "\n", encoding="ascii"
        )
        staged |= {f"family/{wave}/FAM{wave}ER.sps"}
        staged |= {f"family/{wave}/FAM{wave}ER.txt"}
    specs = loader.individual_specs(registries)
    directory = root / "ind2023er"
    directory.mkdir()
    (directory / "IND2023ER.sps").write_text(_setup(specs))
    (directory / "IND2023ER.txt").write_text(
        "\n".join(_individual_lines(inputs, specs)) + "\n", encoding="ascii"
    )
    staged |= {"ind2023er/IND2023ER.sps", "ind2023er/IND2023ER.txt"}
    return staged


#: An invented authorization record for the unfrozen loads here, on the
#: invented staged directory only: the section 20 step-4 pass needs Max's
#: recorded authorization (a chief-of-staff decision), and this
#: placeholder id is not one.
TEST_AUTHORIZATION = {
    "decision": "d999999999",
    "git_head": "0" * 40,
    "recorded_at_utc": "2026-10-12T00:00:00Z",
}


def _load(
    root,
    inputs: cohort.U2Inputs,
    *,
    evidence=None,
    history: pd.DataFrame | None = None,
    source_hashes: dict[str, str] | None = None,
) -> cohort.U2Inputs:
    """Run the real loader on ``root`` with the four named patches
    (``evidence`` is passed through; ``history`` replaces the invented
    marriage history the patched reader returns; ``source_hashes`` is what
    the patched cited-source rehash returns, nothing by default)."""

    cited = {} if source_hashes is None else dict(source_hashes)

    history = inputs.marriage_history if history is None else history

    # The committed role rules are cached on first use; compute them
    # before ``blockers`` is patched so the cache holds the real rules.
    sources.RoleContext.from_registry()
    patch = pytest.MonkeyPatch()
    try:
        patch.setattr(sources, "blockers", lambda entry, name: [])
        patch.setattr(
            loader, "check_source_hashes", lambda registries, data_dir: cited
        )
        patch.setattr(
            marriage,
            "marriage_history",
            lambda *, data_dir=None, nrows=None: history,
        )
        patch.setattr(
            family,
            "family_earnings_panel",
            lambda *, waves=None, data_dir=None: inputs.observed_earnings,
        )
        if evidence is not None:
            patch.setattr(
                loader,
                "read_preregistration_evidence",
                lambda *args, **kwargs: loader.check_preregistration_evidence(
                    evidence
                ),
            )
        _GUARD["active"], _GUARD["opened"] = True, []
        if evidence is None:
            return loader.load_u2_inputs(
                data_dir=root, authorization=TEST_AUTHORIZATION
            )
        return loader.load_u2_inputs(data_dir=root, evidence=evidence)
    finally:
        _GUARD["active"] = False
        patch.undo()


@pytest.fixture(scope="module")
def loaded(tmp_path_factory, u2_inputs, committed_registries):
    """The invented staged directory read by the real loader."""

    root = tmp_path_factory.mktemp("invented-psid")
    staged = _stage(root, u2_inputs, committed_registries)
    inputs = _load(root, u2_inputs)
    return {"inputs": inputs, "root": root, "staged": staged}


def test_stage_three_reads_and_hashes_exactly_the_staged_files(loaded):
    inputs = loaded["inputs"]
    assert _GUARD["opened"] == []
    recorded = dict(inputs.provenance["psid_files_sha256"])
    assert set(recorded) == loaded["staged"]
    import hashlib

    for relative, digest in recorded.items():
        raw = (loaded["root"] / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
    assert inputs.provenance["kind"] == cohort.PSID_FILES
    assert inputs.provenance["psid_data_dir"] == str(loaded["root"])
    assert inputs.provenance["registries"]["kind"] == "committed"


def test_stage_three_seals_the_frames(loaded):
    inputs = loaded["inputs"]
    assert inputs.loader_seal["input_frames_sha256"] == (
        cohort.input_frames_sha256(inputs)
    )
    provenance = cohort._input_provenance(inputs)
    assert provenance["kind"] == cohort.PSID_FILES
    assert provenance["psid_files_sha256"] == dict(
        inputs.provenance["psid_files_sha256"]
    )
    assert inputs.invented_seal is None


def test_stage_three_frames_equal_the_invented_population(loaded, u2_inputs):
    inputs = loaded["inputs"]
    for wave in sources.SUPPORT_WAVES:
        expected = u2_inputs.anchors[wave].assign(
            weight=u2_inputs.anchors[wave]["weight"].round()
        )
        pd.testing.assert_frame_equal(
            inputs.anchors[wave].reset_index(drop=True),
            expected.reset_index(drop=True),
        )
        pd.testing.assert_frame_equal(
            inputs.family_income[wave].reset_index(drop=True),
            u2_inputs.family_income[wave].reset_index(drop=True),
        )
        pd.testing.assert_frame_equal(
            inputs.family_wealth[wave].reset_index(drop=True),
            u2_inputs.family_wealth[wave].reset_index(drop=True),
        )
    pd.testing.assert_frame_equal(
        inputs.persons.reset_index(drop=True),
        u2_inputs.persons.reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(
        inputs.design.reset_index(drop=True),
        u2_inputs.design.reset_index(drop=True),
    )


def test_stage_three_applies_the_registry_dc_route(
    loaded, u2_inputs, committed_registries
):
    """The loader's DC balances are the registry route's (never the
    declared route's) on the same invented items."""

    inputs = loaded["inputs"]
    patch = pytest.MonkeyPatch()
    try:
        patch.setattr(sources, "blockers", lambda entry, name: [])
        gate = sources.SourceGate(sources.REGISTRY, committed_registries)
        for wave in sources.SUPPORT_WAVES:
            route = sources.dc_route(wave, gate)
            assert route.source == "pension_registry_routes"
            raw = invented.raw_family_frame(u2_inputs, wave)
            items = raw[
                ["interview"]
                + [
                    spec.concept
                    for spec in sources.pension_field_specs(wave, gate)
                ]
            ]
            widths = {
                spec.concept: spec.width
                for spec in sources.pension_field_specs(wave, gate)
                if spec.concept.endswith("_amount")
            }
            expected = sources.employer_dc_balances(items, route, widths)
            pd.testing.assert_frame_equal(
                inputs.employer_dc[wave].reset_index(drop=True),
                expected.reset_index(drop=True),
            )
    finally:
        patch.undo()


def test_loaded_inputs_take_the_registered_path_only(
    loaded, frozen_load, evidence, declared
):
    """Sealed psid_files inputs: the registered guard accepts them only
    once the loader rechecked them against the frozen pre-registration
    evidence (review round 1, finding 2) and they match the record the
    registration binds (review round 3); the declared role context
    refuses them.  The committed roles registry, which since Max's d1090
    ruling resolves every code these invented records hold, builds them
    and applies the section 16c exclusions."""

    inputs = loaded["inputs"]
    registry = sources.RoleContext.from_registry()
    with pytest.raises(runner.U2RunError, match="frozen pre-registration"):
        runner.check_inputs(inputs, ap.REGISTERED_REAL, POINTER, registry)
    rechecked = frozen_load["inputs"]
    assert runner.check_inputs(
        rechecked,
        ap.REGISTERED_REAL,
        POINTER,
        registry,
        preregistration_evidence_sha256=frozen_load["sha256"],
        preregistration_evidence=evidence,
    ) == {
        cohort.EVIDENCE_KEY: frozen_load["sha256"],
        "input_frames_sha256": evidence["input_frames_sha256"],
    }
    with pytest.raises(runner.U2RunError, match="invented"):
        runner.check_inputs(inputs, ap.INVENTED, None, registry)
    with pytest.raises(cohort.U2CohortError, match="invented inputs"):
        cohort.build_u2_cohort(inputs, role_context=declared)
    built = cohort.build_u2_cohort(inputs, role_context=registry)
    assert built.provenance["role_context"] == sources.REGISTRY
    assert set(sources.FAMILY_UNIT_EXCLUSIONS) <= set(
        built.dispositions["disposition"]
    )


def test_a_changed_frame_breaks_the_seal(loaded):
    import dataclasses

    inputs = loaded["inputs"]
    changed = dataclasses.replace(
        inputs, anchors={**inputs.anchors, 2019: inputs.anchors[2019].copy()}
    )
    assert changed.loader_seal is None
    with pytest.raises(cohort.U2CohortError, match="U2 loader"):
        cohort._input_provenance(changed)


def test_the_individual_setup_is_cross_checked(tmp_path, committed_registries):
    specs = loader.individual_specs(committed_registries)
    good = tmp_path / "good.sps"
    good.write_text(_setup(specs))
    assert loader.check_layouts_against_setup(specs, good) == len(specs)
    moved = [spec if spec.concept != "2019.weight" else None for spec in specs]
    shifted = next(s for s in specs if s.concept == "2019.weight")
    bad = tmp_path / "bad.sps"
    bad.write_text(
        _setup([s for s in moved if s is not None]).replace(
            "\n.\n",
            f"\n   {shifted.variable} {shifted.start + 1} - "
            f"{shifted.end + 1}\n.\n",
        )
    )
    with pytest.raises(loader.U2LoaderRefusal, match="differ"):
        loader.check_layouts_against_setup(specs, bad)


def test_individual_and_weight_registries_must_agree(committed_registries):
    import copy

    documents = copy.deepcopy(dict(committed_registries.documents))
    for entry in documents["weights"]["entries"]:
        if entry["id"] == "2019.cross_section_weight":
            entry["variable"] = "ER00000"
    invented_set = sources.RegistrySet(
        documents, dict(committed_registries.sha256), "invented"
    )
    with pytest.raises(loader.U2LoaderRefusal, match="weights registry"):
        loader.individual_specs(invented_set)


def test_a_moved_individual_column_refuses_the_load(
    tmp_path, u2_inputs, committed_registries
):
    """Review 2, finding 5: the individual file's staged setup must agree
    with the registry layouts before it is read; a setup that moves one
    column refuses the load."""

    _stage(tmp_path, u2_inputs, committed_registries)
    setup = tmp_path / "ind2023er" / "IND2023ER.sps"
    specs = loader.individual_specs(committed_registries)
    weight = next(spec for spec in specs if spec.concept == "2019.weight")
    text = setup.read_text()
    old = f"   {weight.variable} {weight.start} - {weight.end}\n"
    assert text.count(old) == 1
    setup.write_text(
        text.replace(
            old,
            f"   {weight.variable} {weight.start + 1} - {weight.end + 1}\n",
        )
    )
    with pytest.raises(loader.U2LoaderRefusal, match="differ"):
        _load(tmp_path, u2_inputs)
    assert _GUARD["opened"] == []


@pytest.mark.parametrize(
    "staged_file, message",
    [
        ("ind2023er/IND2023ER.txt", "duplicate person_id"),
        ("family/2019/FAM2019ER.txt", "duplicate interview"),
    ],
)
def test_a_repeated_record_refuses_the_load(
    tmp_path, u2_inputs, committed_registries, staged_file, message
):
    """Section 14: duplicate identifiers refuse execution.  A staged file
    that repeats its first record (the individual file's person, a
    family file's interview) refuses the load."""

    _stage(tmp_path, u2_inputs, committed_registries)
    path = tmp_path / staged_file
    lines = path.read_text(encoding="ascii").splitlines()
    path.write_text("\n".join([*lines, lines[0]]) + "\n", encoding="ascii")
    with pytest.raises(
        (loader.U2LoaderRefusal, sources.U2SourceRefusal), match=message
    ):
        _load(tmp_path, u2_inputs)
    assert _GUARD["opened"] == []


# ---------------------------------------------------------------------------
# Review round 1, finding 1: individual-file values against the registry's
# documented codes.  Each case rewrites one field of one staged record.
# ---------------------------------------------------------------------------
def _rewrite_individual_field(root, registries, person_id, key, text):
    """Put ``text`` (right-justified) in field ``key`` of ``person_id``'s
    staged individual record; return the field's previous text."""

    specs = {
        spec.concept: spec for spec in loader.individual_specs(registries)
    }
    family, number = (
        specs["common.person_family_id"],
        specs["common.person_number"],
    )
    target = specs[key]
    path = root / "ind2023er" / "IND2023ER.txt"
    lines = path.read_text(encoding="ascii").splitlines()
    for index, line in enumerate(lines):
        pid = int(line[family.start - 1 : family.end]) * 1000 + int(
            line[number.start - 1 : number.end]
        )
        if pid != person_id:
            continue
        assert len(text) <= target.width, (key, text)
        old = line[target.start - 1 : target.end]
        lines[index] = (
            line[: target.start - 1]
            + text.rjust(target.width)
            + line[target.end :]
        )
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        return old.strip()
    raise AssertionError(f"no staged record for {person_id}")


#: ``(key, person, documented staged value, undocumented replacement)``.
#: The first two are the round-1 review's minimal cases: single head
#: 700031's sex 2 -> 5 (accepted and set to "na" before the fix, dropping
#: an observation), and 700142 -- the 2015 legal spouse (code 90) of U0
#: head 700141 -- relationship 90 -> 99 (99 is undocumented in every
#: wave; before the fix the head silently lost the legal-spouse pairing).
UNDOCUMENTED_CASES = [
    ("common.sex", 700031, "2", "5"),
    ("2015.relationship", 700142, "90", "99"),
    ("2013.relationship", 700142, None, "92"),
    ("2019.sequence", 700142, None, "30"),
    ("common.stratum", 700142, None, "95"),
    ("common.cluster", 700142, None, "3"),
    ("2021.age", 700142, None, "126"),
    ("2017.reported_birth_year", 700142, None, "2018"),
    ("2023.interview", 700142, None, "-1"),
    ("2019.weight", 700142, None, "-1"),
    ("common.person_number", 700142, None, "0"),
    ("2015.relationship", 700142, None, ""),
]


@pytest.mark.parametrize(
    "key, person, before, value",
    UNDOCUMENTED_CASES,
    ids=[f"{case[0]}={case[3] or 'blank'}" for case in UNDOCUMENTED_CASES],
)
def test_an_undocumented_individual_value_refuses_the_load(
    tmp_path, u2_inputs, committed_registries, key, person, before, value
):
    """Section 14 ("refuse, never fall back"): one undocumented value in
    one staged individual record refuses the whole load with the named
    :class:`loader.U2UndocumentedValue`, as the family-file parse refuses
    out-of-domain values."""

    _stage(tmp_path, u2_inputs, committed_registries)
    old = _rewrite_individual_field(
        tmp_path, committed_registries, person, key, value
    )
    if before is not None:
        assert old == before
    with pytest.raises(loader.U2LoaderRefusal) as refusal:
        _load(tmp_path, u2_inputs)
    assert type(refusal.value).__name__ == "U2UndocumentedValue"
    assert f"individual:{key}" in str(refusal.value)
    assert _GUARD["opened"] == []


def test_the_undocumented_value_message_prints_codes_never_identifiers(
    tmp_path, u2_inputs, committed_registries
):
    _stage(tmp_path, u2_inputs, committed_registries)
    _rewrite_individual_field(
        tmp_path, committed_registries, 700031, "common.sex", "5"
    )
    with pytest.raises(loader.U2LoaderRefusal, match=r"codes \[5\]"):
        _load(tmp_path, u2_inputs)
    _stage(tmp_path / "ids", u2_inputs, committed_registries)
    _rewrite_individual_field(
        tmp_path / "ids", committed_registries, 700142, "2021.age", "126"
    )
    with pytest.raises(loader.U2LoaderRefusal) as refusal:
        _load(tmp_path / "ids", u2_inputs)
    assert "126" not in str(refusal.value)
    assert "700142" not in str(refusal.value)


@pytest.mark.parametrize(
    "key, person, value",
    [
        ("common.sex", 700031, "9"),
        ("2015.relationship", 700142, "98"),
        ("2021.age", 700142, "999"),
        ("2017.reported_birth_year", 700142, "9999"),
    ],
)
def test_a_documented_value_still_loads(
    tmp_path, u2_inputs, committed_registries, key, person, value
):
    """The check refuses only undocumented values: a documented code
    (sex 9 NA, relationship 98, age 999, year born 9999) still loads, and
    sex 9 is the only code read as "na"."""

    _stage(tmp_path, u2_inputs, committed_registries)
    _rewrite_individual_field(
        tmp_path, committed_registries, person, key, value
    )
    inputs = _load(tmp_path, u2_inputs)
    if key == "common.sex":
        sex = inputs.persons.set_index("person_id")["sex"]
        assert sex.loc[person] == "na"
        assert set(sex) <= {"male", "female", "na"}


def _raw_individual(inputs, registries) -> pd.DataFrame:
    """The invented population as the individual reader's raw columns."""

    specs = loader.individual_specs(registries)
    lines = _individual_lines(inputs, specs)
    return pd.DataFrame(
        {
            spec.variable: [
                int(line[spec.start - 1 : spec.end]) for line in lines
            ]
            for spec in specs
        }
    )


def _documented_by_codebook(entry, value: int) -> bool:
    """The test's own oracle: the entry's ``codes`` or the codebook range
    (the ranges are held to the registry text below)."""

    if entry["codes"]:
        return str(value) in entry["codes"]
    concept = entry["concept"]
    if concept == "age":
        return value in (0, 999) or 1 <= value <= 125
    if concept == "reported_birth_year":
        return value in (0, 9999) or 1870 <= value <= int(entry["wave"])
    if concept == "interview":
        return 0 <= value <= 99_999
    if concept == "weight":
        return value >= 0
    assert concept in ("person_family_id", "person_number"), concept
    return value >= 1


_KEYS = [
    spec.concept
    for spec in loader.individual_specs(sources.RegistrySet.committed())
]


@pytest.fixture(scope="module")
def raw_individual(u2_inputs, committed_registries):
    return _raw_individual(u2_inputs, committed_registries)


@settings(max_examples=200, deadline=None)
@given(
    key=st.sampled_from(_KEYS),
    value=st.one_of(
        st.integers(min_value=-5, max_value=130),
        st.integers(min_value=1860, max_value=2030),
        st.sampled_from([999, 9998, 9999, 99_999, 100_000]),
    ),
    row=st.integers(min_value=0, max_value=75),
)
def test_the_individual_check_accepts_exactly_the_documented_domain(
    raw_individual, committed_registries, key, value, row
):
    """Invariant: for every field U2 reads and every integer value, the
    check refuses one record holding it iff the registry does not
    document it (and leaves every documented value to load)."""

    raw = raw_individual.copy()
    assert loader.check_individual_values(raw, committed_registries)
    entry = committed_registries.entry("individual", key)
    raw.loc[row % len(raw), entry["variable"]] = value
    documented = _documented_by_codebook(entry, value)
    if documented:
        checked = loader.check_individual_values(raw, committed_registries)
        assert checked[key] == len(raw)
    else:
        with pytest.raises(loader.U2UndocumentedValue, match=key):
            loader.check_individual_values(raw, committed_registries)


def test_the_documented_ranges_are_the_registry_codebook_text(
    committed_registries,
):
    """The ranges the loader restates for fields without ``codes`` are
    the ones every wave's codebook text prints; the sex codes it maps are
    exactly common.sex's."""

    for wave in sources.SUPPORT_WAVES:
        age = committed_registries.entry("individual", f"{wave}.age")
        assert age["codes"] == {}
        for line in (
            "1 Newborn up to second birthday",
            "2 - 125 Actual age",
            "999 DK; NA; refused",
            "0 Inap.",
        ):
            assert line in age["codebook_text"], (wave, line)
        born = committed_registries.entry(
            "individual", f"{wave}.reported_birth_year"
        )
        assert list(born["missing_codes"]) == [0, 9999]
        assert (
            f"1,870 - {wave // 1000},{wave % 1000:03d} Actual year of birth"
            in born["codebook_text"]
        )
        interview = committed_registries.entry(
            "individual", f"{wave}.interview"
        )
        assert interview["codes"] == {}
        assert interview["layout"]["width"] == 5
        assert "0 Inap." in interview["codebook_text"]
        weight = committed_registries.entry("individual", f"{wave}.weight")
        assert "do not infer a domain" in weight["selection"]
    sex = committed_registries.entry("individual", "common.sex")
    assert {int(code) for code in sex["codes"]} == set(loader._PERSON_SEX)
    assert loader._AGE_CODES == (0, 999)
    assert loader._AGE_RANGE == (1, 125)
    assert loader._FIRST_BIRTH_YEAR == 1870


def test_an_undocumented_relationship_code_has_no_ofum_rule(declared):
    """Finding 1's second path: a relationship code no wave documents
    (99), code 92 before 2017, and code 0 ("Inap.") on an in-family
    member refuse in both role contexts; a documented code outside
    section 3's table still takes the inherited OFUM rule."""

    registry = sources.RoleContext.from_registry()
    for context in (registry, declared):
        for wave in sources.SUPPORT_WAVES:
            for code in (99, 1, 0):
                with pytest.raises(sources.U2RoleRefusal):
                    context.rule(wave, code)
            rule = context.rule(wave, 30)
            assert (rule.income_role, rule.spouse_slot) == ("ofum", False)
        for wave in (2013, 2015):
            with pytest.raises(sources.U2RoleRefusal):
                context.rule(wave, 92)


# ---------------------------------------------------------------------------
# Review round 1, finding 2: the frozen PSID file and frame identities.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def evidence(loaded):
    """The evidence record the step-4 pass would write from the staged
    invented files (INVENTED DATA - NOT A COMPARISON)."""

    return loader.preregistration_evidence(loaded["inputs"])


@pytest.fixture(scope="module")
def frozen_load(loaded, evidence, u2_inputs):
    """The same staged directory reloaded against its frozen evidence."""

    inputs = _load(loaded["root"], u2_inputs, evidence=evidence)
    return {
        "inputs": inputs,
        "sha256": loader.preregistration_evidence_sha256(evidence),
    }


def test_the_evidence_freezes_every_file_read_and_the_frame_digest(
    loaded, evidence
):
    inputs = loaded["inputs"]
    assert evidence["target_id"] == "U2"
    assert evidence["psid_files_sha256"] == dict(
        sorted(inputs.provenance["psid_files_sha256"].items())
    )
    assert set(evidence["psid_files_sha256"]) == loaded["staged"]
    assert evidence["input_frames_sha256"] == (
        inputs.loader_seal["input_frames_sha256"]
    )
    assert evidence["psid_files_bundle_sha256"] == (
        inputs.loader_seal["psid_files_bundle_sha256"]
    )
    assert evidence["registries_sha256"] == dict(
        sorted(sources.REGISTRY_SHA256.items())
    )
    assert "psid_data_dir" not in evidence
    assert loader.check_preregistration_evidence(evidence) == evidence


def test_a_frozen_reload_matches_and_seals_the_evidence(
    loaded, frozen_load, evidence
):
    inputs = frozen_load["inputs"]
    assert _GUARD["opened"] == []
    assert inputs.loader_seal[cohort.EVIDENCE_KEY] == frozen_load["sha256"]
    assert inputs.provenance[cohort.EVIDENCE_KEY] == frozen_load["sha256"]
    provenance = cohort._input_provenance(inputs)
    assert provenance[cohort.EVIDENCE_KEY] == frozen_load["sha256"]
    assert provenance["input_frames_sha256"] == (
        evidence["input_frames_sha256"]
    )
    # The unfrozen load's seal is unchanged (no evidence key).
    assert cohort.EVIDENCE_KEY not in loaded["inputs"].loader_seal


def _flip_one_byte(path: Path, offset: int) -> bytes:
    raw = path.read_bytes()
    old = raw[offset : offset + 1]
    new = b"7" if old != b"7" else b"8"
    path.write_bytes(raw[:offset] + new + raw[offset + 1 :])
    return raw


def _amount_offset(root, committed_registries) -> int:
    """The byte offset of a digit inside a 2019 amount field, so the
    changed file still parses (the unfrozen load accepts it)."""

    gate = sources.SourceGate(sources.INVENTED_DECLARED, committed_registries)
    spec = next(
        spec
        for spec in loader.family_record_specs(2019, gate)
        if spec.concept == "head_labor"
    )
    first = (
        (root / "family" / "2019" / "FAM2019ER.txt")
        .read_text(encoding="ascii")
        .splitlines()[0]
    )
    return spec.end - 1 if first[spec.end - 1].isdigit() else spec.end - 2


def test_one_changed_byte_refuses_the_frozen_load(
    tmp_path, u2_inputs, committed_registries, evidence
):
    """Section 14: "changed source bytes ... refuse execution".  A digit
    changed in a 2019 amount field leaves a parseable file the unfrozen
    load accepts with other frames; against the frozen evidence the same
    change refuses before any record is parsed."""

    _stage(tmp_path, u2_inputs, committed_registries)
    path = tmp_path / "family" / "2019" / "FAM2019ER.txt"
    _flip_one_byte(path, _amount_offset(tmp_path, committed_registries))
    changed = _load(tmp_path, u2_inputs)
    assert changed.loader_seal["input_frames_sha256"] != (
        evidence["input_frames_sha256"]
    )
    parsed = []
    patch = pytest.MonkeyPatch()
    original = sources.parse_fixed_width
    patch.setattr(
        sources,
        "parse_fixed_width",
        lambda *a, **k: parsed.append(1) or original(*a, **k),
    )
    try:
        with pytest.raises(
            loader.U2LoaderRefusal, match="changed source bytes"
        ) as refusal:
            _load(tmp_path, u2_inputs, evidence=evidence)
    finally:
        patch.undo()
    assert type(refusal.value).__name__ == "U2FrozenIdentityMismatch"
    assert "family/2019/FAM2019ER.txt" in str(refusal.value)
    assert parsed == []
    assert _GUARD["opened"] == []


@pytest.mark.parametrize(
    "relative",
    [
        "ind2023er/IND2023ER.txt",
        "ind2023er/IND2023ER.sps",
        "family/2013/FAM2013ER.sps",
        "family/2023/FAM2023ER.txt",
    ],
)
def test_any_changed_or_missing_staged_file_refuses(
    tmp_path, u2_inputs, committed_registries, evidence, relative
):
    _stage(tmp_path, u2_inputs, committed_registries)
    _flip_one_byte(tmp_path / relative, 0)
    with pytest.raises(loader.U2LoaderRefusal, match="1 frozen PSID file"):
        _load(tmp_path, u2_inputs, evidence=evidence)
    (tmp_path / relative).unlink()
    with pytest.raises(loader.U2LoaderRefusal, match="1 missing"):
        _load(tmp_path, u2_inputs, evidence=evidence)


def test_a_changed_frame_digest_refuses(
    tmp_path, u2_inputs, committed_registries, evidence
):
    """Section 14: "changed frame digests ... refuse".  Every staged file
    is unchanged, but the (patched) marriage-history reader returns other
    frames: the digest check after reading refuses."""

    _stage(tmp_path, u2_inputs, committed_registries)
    history = u2_inputs.marriage_history.iloc[1:].reset_index(drop=True)
    with pytest.raises(loader.U2LoaderRefusal, match="frame digest|digest"):
        _load(tmp_path, u2_inputs, evidence=evidence, history=history)


@pytest.mark.parametrize(
    "relative",
    [
        # Each reader's own opener: the family file through Path.open, a
        # setup file through the layout parser, the individual file
        # through pandas (review of the d745 and 1a-1c answers, nit 1).
        "family/2017/FAM2017ER.txt",
        "family/2013/FAM2013ER.sps",
        "ind2023er/IND2023ER.txt",
    ],
)
def test_a_file_read_but_not_frozen_refuses_at_open(
    tmp_path, u2_inputs, committed_registries, evidence, relative
):
    """Review of 630a68c3, finding 1: a file under the PSID directory that
    the record does not freeze is refused when it is opened, before any
    reader returns its contents."""

    _stage(tmp_path, u2_inputs, committed_registries)
    files = dict(evidence["psid_files_sha256"])
    files.pop(relative)
    narrower = {
        **evidence,
        "psid_files_sha256": files,
        "psid_files_bundle_sha256": loader.files_bundle_sha256(files),
    }
    parsed, layouts, products = [], [], []
    patch = pytest.MonkeyPatch()
    family_reader = loader.read_family_records
    layout_reader = psid.parse_sps_layout
    product_reader = psid.read_psid
    patch.setattr(
        loader,
        "read_family_records",
        lambda handle, wave, gate: parsed.append(wave)
        or family_reader(handle, wave, gate),
    )

    def layout(path):
        frame = layout_reader(path)
        layouts.append(Path(path).relative_to(tmp_path).as_posix())
        return frame

    def product(name, *args, **kwargs):
        frame = product_reader(name, *args, **kwargs)
        products.append(name)
        return frame

    patch.setattr(psid, "parse_sps_layout", layout)
    patch.setattr(psid, "read_psid", product)
    try:
        with pytest.raises(
            loader.U2FrozenIdentityMismatch,
            match=f"{relative} is under the PSID directory but not in the "
            "frozen",
        ):
            _load(tmp_path, u2_inputs, evidence=narrower)
    finally:
        patch.undo()
    if relative == "family/2017/FAM2017ER.txt":
        assert parsed == [2013, 2015]
    elif relative == "family/2013/FAM2013ER.sps":
        assert parsed == [] and relative not in layouts
    else:
        assert parsed == list(sources.SUPPORT_WAVES)
        assert "ind2023er" not in products


def test_frozen_cited_sources_must_match(
    tmp_path, u2_inputs, committed_registries, evidence
):
    """The setup files and codebooks the registries cite must hash as the
    evidence froze them; a difference refuses before any family record is
    parsed (review of the d745 and 1a-1c answers, nit 2)."""

    _stage(tmp_path, u2_inputs, committed_registries)
    parsed = []
    patch = pytest.MonkeyPatch()
    original = loader.read_family_records
    patch.setattr(
        loader,
        "read_family_records",
        lambda handle, wave, gate: parsed.append(wave)
        or original(handle, wave, gate),
    )
    try:
        with pytest.raises(
            loader.U2FrozenIdentityMismatch,
            match="cited setup files and codebooks differ",
        ):
            _load(
                tmp_path,
                u2_inputs,
                evidence=evidence,
                source_hashes={"PSID/family/2019/FAM2019ER.sps": "a" * 64},
            )
    finally:
        patch.undo()
    assert parsed == []


def test_a_frozen_load_needs_the_committed_record(
    tmp_path, evidence, monkeypatch
):
    """Review of 630a68c3, finding 1: a frozen load reads PSID records only
    against the committed pre-registration record, so a fabricated record,
    however well-formed, cannot stand in for the authorization an unfrozen
    load needs.  It refuses before any PSID path is resolved or any file
    opened: while no record is committed, and when the committed one
    differs."""

    import sys

    from populace_dynamics.data import psid

    resolved, opened = [], []

    def spy(event, args):
        if event == "open" and args and str(args[0]).startswith(str(tmp_path)):
            opened.append(str(args[0]))

    sys.addaudithook(spy)
    original = psid._resolve_data_dir
    monkeypatch.setattr(
        psid,
        "_resolve_data_dir",
        lambda data_dir: resolved.append(data_dir) or original(data_dir),
    )
    assert not loader.PREREGISTRATION_EVIDENCE_PATH.exists()
    with pytest.raises(
        loader.U2FrozenIdentityMismatch, match="no pre-registration evidence"
    ):
        loader.load_u2_inputs(data_dir=tmp_path, evidence=evidence)
    committed = {**evidence, "input_frames_sha256": "0" * 64}
    monkeypatch.setattr(
        loader,
        "read_preregistration_evidence",
        lambda *args, **kwargs: loader.check_preregistration_evidence(
            committed
        ),
    )
    with pytest.raises(
        loader.U2FrozenIdentityMismatch,
        match="not the committed pre-registration record",
    ):
        loader.load_u2_inputs(data_dir=tmp_path, evidence=evidence)
    assert resolved == [] and opened == []


def _altered(evidence, **changes):
    record = {**evidence, **changes}
    return record


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda e: _altered(e, schema_version="v0"), "schema"),
        (lambda e: _altered(e, target_id="U1"), "not 'U2'"),
        (lambda e: _altered(e, specification="other"), "specification"),
        (
            lambda e: _altered(
                e,
                registries_sha256={
                    **e["registries_sha256"],
                    "roles": "0" * 64,
                },
            ),
            "registries other than",
        ),
        (
            lambda e: _altered(e, input_frames_sha256="ABC"),
            "input_frames_sha256",
        ),
        (
            lambda e: _altered(e, psid_files_bundle_sha256="0" * 64),
            "bundle",
        ),
        (
            lambda e: _altered(
                e,
                psid_files_sha256={"/etc/passwd": "0" * 64},
                psid_files_bundle_sha256=loader.files_bundle_sha256(
                    {"/etc/passwd": "0" * 64}
                ),
            ),
            "relative",
        ),
        (
            lambda e: _altered(
                e,
                psid_files_sha256={"../x.txt": "0" * 64},
                psid_files_bundle_sha256=loader.files_bundle_sha256(
                    {"../x.txt": "0" * 64}
                ),
            ),
            "relative",
        ),
        (
            lambda e: _altered(
                e,
                psid_files_sha256={},
                psid_files_bundle_sha256=loader.files_bundle_sha256({}),
            ),
            "no PSID file",
        ),
        (lambda e: {**e, "extra": 1}, "not exactly"),
        # Round 3, second pass: only plain JSON data, by exact type.
        (
            lambda e: {
                **e,
                "input_frames_sha256": type("_S", (str,), {})(
                    e["input_frames_sha256"]
                ),
            },
            "plain JSON",
        ),
        (
            lambda e: {
                **e,
                "psid_files_sha256": MappingProxyType(e["psid_files_sha256"]),
            },
            "plain JSON",
        ),
        (
            lambda e: {
                **e,
                "psid_files_sha256": {
                    type("_S", (str,), {})(key): value
                    for key, value in e["psid_files_sha256"].items()
                },
            },
            "plain JSON",
        ),
        (
            lambda e: {k: v for k, v in e.items() if k != "target_id"},
            "not exactly",
        ),
    ],
)
def test_a_malformed_evidence_record_refuses(evidence, change, message):
    with pytest.raises(loader.U2LoaderRefusal, match=message):
        loader.check_preregistration_evidence(change(dict(evidence)))


def test_an_absent_evidence_record_refuses(tmp_path):
    with pytest.raises(loader.U2LoaderRefusal, match="no pre-registration"):
        loader.read_preregistration_evidence(tmp_path / "absent.json")
    path = tmp_path / "evidence.json"
    path.write_text("not json")
    with pytest.raises(loader.U2LoaderRefusal, match="not JSON"):
        loader.read_preregistration_evidence(path)


def test_the_committed_evidence_record_is_absent_so_registration_refuses():
    """At this commit the section 20 step-4 pass has not run: there is no
    committed evidence record, so the registered run cannot bind one."""

    assert not loader.PREREGISTRATION_EVIDENCE_PATH.exists()
    with pytest.raises(loader.U2LoaderRefusal, match="no pre-registration"):
        loader.read_preregistration_evidence()


def test_evidence_is_recorded_only_from_loader_sealed_inputs(
    loaded, u2_inputs
):
    with pytest.raises(loader.U2LoaderRefusal, match="loader sealed"):
        loader.preregistration_evidence(u2_inputs)
    labelled = cohort.replace_provenance(u2_inputs, kind=cohort.PSID_FILES)
    with pytest.raises(cohort.U2CohortError, match="U2 loader"):
        loader.preregistration_evidence(labelled)


def test_a_forged_evidence_seal_refuses(loaded, frozen_load):
    """The evidence hash counts only when the seal and the provenance
    both carry it, as the loader wrote them."""

    import dataclasses

    unfrozen = loaded["inputs"]
    forged = dataclasses.replace(
        unfrozen,
        provenance={
            **unfrozen.provenance,
            cohort.EVIDENCE_KEY: frozen_load["sha256"],
        },
    )
    object.__setattr__(forged, "loader_seal", dict(unfrozen.loader_seal))
    with pytest.raises(cohort.U2CohortError, match="sealed"):
        cohort._input_provenance(forged)
    rechecked = frozen_load["inputs"]
    stripped = dataclasses.replace(
        rechecked,
        provenance={
            k: v
            for k, v in rechecked.provenance.items()
            if k != cohort.EVIDENCE_KEY
        },
    )
    object.__setattr__(stripped, "loader_seal", dict(rechecked.loader_seal))
    with pytest.raises(cohort.U2CohortError, match="sealed"):
        cohort._input_provenance(stripped)


@pytest.fixture(scope="module")
def frozen_stage(tmp_path_factory, u2_inputs, committed_registries):
    root = tmp_path_factory.mktemp("frozen-stage")
    _stage(root, u2_inputs, committed_registries)
    files = {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in sorted(
            str(path.relative_to(root))
            for path in root.rglob("*")
            if path.is_file()
        )
    }
    record = {
        "schema_version": loader.PREREGISTRATION_SCHEMA,
        "target_id": "U2",
        "specification": "boomers2004_1946_55_uniform_cut",
        "registries_sha256": dict(sources.REGISTRY_SHA256),
        "cited_sources_sha256": {},
        "psid_files_sha256": files,
        "psid_files_bundle_sha256": loader.files_bundle_sha256(files),
        "input_frames_sha256": "0" * 64,
    }
    return {"root": root, "evidence": record, "files": sorted(files)}


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_every_single_byte_change_to_any_frozen_file_refuses(
    frozen_stage, data
):
    """Invariant: for every frozen file, byte offset and replacement byte,
    the pre-read recheck refuses; with the bytes restored it passes."""

    root, record = frozen_stage["root"], frozen_stage["evidence"]
    relative = data.draw(st.sampled_from(frozen_stage["files"]))
    path = root / relative
    raw = path.read_bytes()
    offset = data.draw(st.integers(0, len(raw) - 1))
    byte = data.draw(
        st.integers(0, 255).filter(lambda value: value != raw[offset])
    )
    path.write_bytes(raw[:offset] + bytes([byte]) + raw[offset + 1 :])
    try:
        with pytest.raises(loader.U2FrozenIdentityMismatch, match="changed"):
            loader.check_frozen_files(record, root)
    finally:
        path.write_bytes(raw)
    assert loader.check_frozen_files(record, root) == (
        record["psid_files_sha256"]
    )


def test_loader_inputs_cannot_join_an_invented_cohort(
    loaded, u2_inputs, u0_cohort
):
    """Review 2, finding 1, on the loader's own output: an invented
    cohort's income rows refuse the sealed psid_files inputs."""

    with pytest.raises(cohort.U2CohortError, match="built from"):
        cohort.income_rows(u0_cohort, loaded["inputs"])


def test_the_loader_seal_is_read_only_and_bound_to_the_file_hashes(loaded):
    import dataclasses

    inputs = loaded["inputs"]
    with pytest.raises(TypeError):
        inputs.loader_seal["input_frames_sha256"] = "0" * 64
    # A seal whose file bundle no longer matches the recorded file
    # hashes is refused (as U1's loader seal is).
    relabelled = dataclasses.replace(
        inputs,
        provenance={
            **inputs.provenance,
            "psid_files_sha256": {"family/2019/FAM2019ER.txt": "0" * 64},
        },
    )
    object.__setattr__(relabelled, "loader_seal", dict(inputs.loader_seal))
    with pytest.raises(cohort.U2CohortError, match="sealed"):
        cohort._input_provenance(relabelled)


# ---------------------------------------------------------------------------
# Review round 2, info 2: a registered run compares the loader's sealed
# evidence hash with the hash its registration binds (not only its shape).
# INVENTED DATA - NOT A COMPARISON: the inputs are the staged invented files.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bound, message",
    [
        (None, "binds"),
        ("0" * 64, "binds"),
        ("not-a-hash", "binds"),
    ],
    ids=["unnamed", "another-record", "malformed"],
)
def test_a_registered_run_needs_the_evidence_its_registration_binds(
    frozen_load, bound, message
):
    registry = sources.RoleContext.from_registry()
    with pytest.raises(runner.U2RunError, match=message):
        runner.check_inputs(
            frozen_load["inputs"],
            ap.REGISTERED_REAL,
            POINTER,
            registry,
            preregistration_evidence_sha256=bound,
        )


def test_an_invented_run_binds_no_evidence(u2_inputs, declared):
    with pytest.raises(runner.U2RunError, match="binds no"):
        runner.check_inputs(
            u2_inputs,
            ap.INVENTED,
            None,
            declared,
            preregistration_evidence_sha256="0" * 64,
        )


class _Reached(Exception):
    pass


def test_a_mismatched_evidence_hash_refuses_before_any_computation(
    frozen_load, monkeypatch
):
    def reached(*args, **kwargs):
        raise _Reached

    monkeypatch.setattr(cohort, "derive_u2_births", reached)
    with pytest.raises(runner.U2RunError, match="binds"):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            preregistration_evidence_sha256="0" * 64,
        )


def test_a_registered_run_computes_with_the_fresh_pinned_read(
    frozen_load, evidence, monkeypatch
):
    """Review round 2: the check verifies the caller's bundle, and the
    run then computes with the fresh read of the pinned files, so an edit
    the caller makes after the check (here, from the progress callback,
    an INVENTED 1.0) never reaches a row."""

    caller = copy.deepcopy(parameters.committed_u2_parameters())
    pinned_value = caller.thresholds.weighted_average[2020]["one_65_plus"]
    seen = []

    def compute_row(row, inputs, params, births, **kwargs):
        seen.append(params)
        raise _Reached

    def progress(message):
        caller.thresholds.weighted_average[2020]["one_65_plus"] = 1.0

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            frozen_load["inputs"],
            caller,
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
            progress=progress,
        )
    assert caller.thresholds.weighted_average[2020]["one_65_plus"] == 1.0
    (used,) = seen
    assert used is not caller
    assert used.thresholds.weighted_average[2020]["one_65_plus"] == (
        pinned_value
    )
    assert parameters.parameters_content_sha256(used) == (
        parameters.parameters_content_sha256(
            parameters.committed_u2_parameters()
        )
    )


# ---------------------------------------------------------------------------
# Review round 3, info 1: the seal is only the loader's own claim.  A seal
# written in-process (``object.__setattr__`` on the frozen dataclass's
# ``init=False`` field) over altered frames repeats that claim, so a
# registered run compares the frames and PSID files with the evidence
# record its registration binds.  Info 2: a registered run computes the
# registered rows only and takes no ``row_set``.
# INVENTED DATA - NOT A COMPARISON: the inputs are the staged invented
# files read back by the loader, and every altered value is an invented
# offset.
# ---------------------------------------------------------------------------
#: INVENTED: added to one cell, as the round-3 review's probe B2 did.
_INVENTED_OFFSET = 5


def _forge(rechecked: cohort.U2Inputs, **frames) -> cohort.U2Inputs:
    """``rechecked`` with ``frames`` replaced under a forged seal.

    The seal is written as the loader writes it, over the changed frames'
    own digest, with the file bundle and the bound evidence hash kept; the
    provenance is the loader's, unchanged.  The forgery is therefore
    internally consistent, and ``cohort._input_provenance`` accepts it.
    """

    import dataclasses

    forged = dataclasses.replace(rechecked, **frames)
    seal = {
        **dict(rechecked.loader_seal),
        "input_frames_sha256": cohort.input_frames_sha256(forged),
    }
    object.__setattr__(forged, "loader_seal", MappingProxyType(seal))
    return forged


def _offset_cell(
    frame: pd.DataFrame, column: str, row: int, offset: int
) -> pd.DataFrame:
    """A copy of ``frame`` with the INVENTED ``offset`` added to one cell
    (a missing cell becomes the offset)."""

    changed = frame.copy()
    position = changed.columns.get_loc(column)
    old = changed.iat[row, position]
    changed.iat[row, position] = offset if pd.isna(old) else old + offset
    return changed


def _income_forgery(rechecked: cohort.U2Inputs) -> cohort.U2Inputs:
    """The review's probe B2: +5 (invented) in one 2019 income cell."""

    income = dict(rechecked.family_income)
    income[2019] = _offset_cell(
        income[2019], "total_family_income", 0, _INVENTED_OFFSET
    )
    return _forge(rechecked, family_income=income)


def _registered_check(inputs, frozen_load, **evidence):
    return runner.check_inputs(
        inputs,
        ap.REGISTERED_REAL,
        POINTER,
        sources.RoleContext.from_registry(),
        preregistration_evidence_sha256=frozen_load["sha256"],
        **evidence,
    )


def test_a_forged_seal_over_altered_frames_passes_only_the_seal_check(
    frozen_load, evidence
):
    """Review round 3, info 1 (probe B2).  The forged seal and the
    loader's provenance agree, so the provenance check accepts the altered
    frames and the bound hash matches the seal.  Before this round the
    registered check accepted them; given only the bound hash it now
    refuses, since it must see the evidence record itself."""

    forged = _income_forgery(frozen_load["inputs"])
    assert cohort.input_frames_sha256(forged) != (
        evidence["input_frames_sha256"]
    )
    provenance = cohort._input_provenance(forged)
    assert provenance[cohort.EVIDENCE_KEY] == frozen_load["sha256"]
    with pytest.raises(runner.U2RunError, match="evidence record"):
        _registered_check(forged, frozen_load)


def test_a_forged_seal_refuses_against_the_bound_evidence_record(
    frozen_load, evidence
):
    forged = _income_forgery(frozen_load["inputs"])
    with pytest.raises(runner.U2RunError, match="frame digest"):
        _registered_check(
            forged, frozen_load, preregistration_evidence=evidence
        )


def test_the_loader_rechecked_inputs_pass_against_the_bound_record(
    frozen_load, evidence
):
    assert _registered_check(
        frozen_load["inputs"], frozen_load, preregistration_evidence=evidence
    ) == {
        cohort.EVIDENCE_KEY: frozen_load["sha256"],
        "input_frames_sha256": evidence["input_frames_sha256"],
    }


def test_relabelled_psid_file_hashes_refuse_against_the_bound_record(
    frozen_load, evidence
):
    """Frames unchanged, but the provenance's file hashes relabelled and
    the seal's bundle forged to match: the provenance check accepts it,
    the evidence record does not."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    files = {
        **dict(rechecked.provenance["psid_files_sha256"]),
        "family/2019/FAM2019ER.txt": "0" * 64,
    }
    bundle = loader.files_bundle_sha256(files)
    forged = dataclasses.replace(
        rechecked,
        provenance={
            **rechecked.provenance,
            "psid_files_sha256": files,
            "psid_files_bundle_sha256": bundle,
        },
    )
    object.__setattr__(
        forged,
        "loader_seal",
        MappingProxyType(
            {**rechecked.loader_seal, "psid_files_bundle_sha256": bundle}
        ),
    )
    assert cohort._input_provenance(forged)["psid_files_sha256"] == files
    with pytest.raises(runner.U2RunError, match="PSID file hashes"):
        _registered_check(
            forged, frozen_load, preregistration_evidence=evidence
        )


def test_relabelled_cited_sources_refuse_against_the_bound_record(
    frozen_load, evidence
):
    import dataclasses

    rechecked = frozen_load["inputs"]
    forged = dataclasses.replace(
        rechecked,
        provenance={
            **rechecked.provenance,
            "cited_sources_sha256": {"PSID/invented.sps": "0" * 64},
        },
    )
    object.__setattr__(forged, "loader_seal", rechecked.loader_seal)
    cohort._input_provenance(forged)
    with pytest.raises(runner.U2RunError, match="cited"):
        _registered_check(
            forged, frozen_load, preregistration_evidence=evidence
        )


@pytest.mark.parametrize(
    "record, message",
    [
        (lambda e: {**e, "input_frames_sha256": "0" * 64}, "hashes to"),
        (lambda e: {**e, "extra": 1}, "not valid"),
        (lambda e: "not a record", "not valid"),
    ],
    ids=["another-record", "malformed", "not-a-mapping"],
)
def test_a_registered_run_needs_the_record_its_bound_hash_names(
    frozen_load, evidence, record, message
):
    with pytest.raises(runner.U2RunError, match=message):
        _registered_check(
            frozen_load["inputs"],
            frozen_load,
            preregistration_evidence=record(dict(evidence)),
        )


def test_an_invented_run_takes_no_evidence_record(
    u2_inputs, declared, evidence
):
    with pytest.raises(runner.U2RunError, match="binds no"):
        runner.check_inputs(
            u2_inputs,
            ap.INVENTED,
            None,
            declared,
            preregistration_evidence=evidence,
        )


def test_a_forged_seal_refuses_before_any_computation(
    frozen_load, evidence, monkeypatch
):
    def reached(*args, **kwargs):
        raise _Reached

    monkeypatch.setattr(cohort, "derive_u2_births", reached)
    with pytest.raises(runner.U2RunError, match="frame digest"):
        runner.run_track_u2(
            _income_forgery(frozen_load["inputs"]),
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )


def _numeric_sites(inputs: cohort.U2Inputs) -> list[tuple]:
    """``(field, wave or None, column)`` of every numeric column of every
    nonempty input frame."""

    sites = []
    for name in ("anchors", "family_income", "family_wealth", "employer_dc"):
        for wave, frame in sorted(getattr(inputs, name).items()):
            if len(frame):
                sites += [
                    (name, wave, column)
                    for column in frame.select_dtypes("number").columns
                ]
    for name in ("design", "persons", "marriage_history", "observed_earnings"):
        frame = getattr(inputs, name)
        if len(frame):
            sites += [
                (name, None, column)
                for column in frame.select_dtypes("number").columns
            ]
    return sites


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_no_seal_forged_over_any_changed_cell_passes_the_registered_check(
    frozen_load, evidence, data
):
    """Invariant (round 3, info 1): for every numeric cell of every input
    frame and every nonzero INVENTED offset, inputs whose seal is forged
    over the changed frames pass the provenance check yet refuse the
    registered check, given only the bound hash and given the bound
    evidence record; the loader's own rechecked inputs pass."""

    rechecked = frozen_load["inputs"]
    name, wave, column = data.draw(
        st.sampled_from(_numeric_sites(rechecked)), label="site"
    )
    frames = getattr(rechecked, name)
    frame = frames if wave is None else frames[wave]
    row = data.draw(st.integers(0, len(frame) - 1), label="row")
    offset = data.draw(
        st.integers(1, 1000) | st.integers(-1000, -1), label="offset"
    )
    changed = _offset_cell(frame, column, row, offset)
    forged = _forge(
        rechecked,
        **{name: changed if wave is None else {**frames, wave: changed}},
    )
    assume(
        cohort.input_frames_sha256(forged) != evidence["input_frames_sha256"]
    )
    assert cohort._input_provenance(forged)[cohort.EVIDENCE_KEY] == (
        frozen_load["sha256"]
    )
    with pytest.raises(runner.U2RunError, match="evidence record"):
        _registered_check(forged, frozen_load)
    with pytest.raises(runner.U2RunError, match="frame digest"):
        _registered_check(
            forged, frozen_load, preregistration_evidence=evidence
        )
    _registered_check(
        rechecked, frozen_load, preregistration_evidence=evidence
    )


def test_a_registered_run_refuses_altered_row_definitions(
    frozen_load, evidence, monkeypatch
):
    """Review round 3, info 2 (probe B3): U0 given the 2 percent interest
    override passed every guard, which checked only the row ids, and
    reached the row computation.  A registered run now refuses any
    ``row_set`` before the inputs are checked."""

    import dataclasses

    altered = {
        **rows.REGISTERED_ROWS,
        "U0": dataclasses.replace(
            rows.REGISTERED_ROWS["U0"], income={"real_interest_rate": 0.02}
        ),
    }
    assert list(altered) == list(rows.ROW_IDS)
    seen = []

    def compute_row(row, *args, **kwargs):
        seen.append(row)
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(runner.U2RunError, match="row_set"):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            row_set=altered,
            preregistration_evidence_sha256=frozen_load["sha256"],
        )
    assert seen == []


def test_a_registered_run_computes_the_registered_rows_by_default(
    frozen_load, evidence, monkeypatch
):
    seen = []

    def compute_row(row, *args, **kwargs):
        seen.append(row)
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )
    (row,) = seen
    assert row is rows.REGISTERED_ROWS[rows.HEADLINE_ROW]


@settings(max_examples=60, deadline=None)
@given(data=st.data())
def test_a_registered_run_refuses_every_row_set_before_any_check(
    frozen_load, u2_params, data
):
    """Invariant (round 3, info 2): a registered run computes exactly
    :data:`rows.REGISTERED_ROWS`, so every ``row_set`` it is given -- the
    registered mapping itself, value-equal copies, or rows carrying
    another registered row's overrides or the unscored 2 percent
    interest -- refuses before the inputs, the parameters or any row are
    touched."""

    import dataclasses

    registered = list(rows.REGISTERED_ROWS.values())
    row_set = {}
    for row in registered:
        kind = data.draw(
            st.sampled_from(("same", "copy", "other", "interest")),
            label=row.row_id,
        )
        if kind == "same":
            row_set[row.row_id] = row
        elif kind == "copy":
            row_set[row.row_id] = dataclasses.replace(row)
        elif kind == "other":
            other = data.draw(st.sampled_from(registered))
            row_set[row.row_id] = dataclasses.replace(
                row, cohort=dict(other.cohort), income=dict(other.income)
            )
        else:
            row_set[row.row_id] = dataclasses.replace(
                row, income={**dict(row.income), "real_interest_rate": 0.02}
            )
    if data.draw(st.booleans(), label="the registered mapping itself"):
        row_set = rows.REGISTERED_ROWS

    def reached(*args, **kwargs):
        raise _Reached

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runner, "check_inputs", reached)
        patch.setattr(parameters, "check_u2_parameters", reached)
        patch.setattr(runner, "_compute_row", reached)
        with pytest.raises(runner.U2RunError, match="row_set"):
            runner.run_track_u2(
                frozen_load["inputs"],
                u2_params,
                data_provenance=ap.REGISTERED_REAL,
                role_context=sources.RoleContext.from_registry(),
                registration_pointer=POINTER,
                row_set=row_set,
                preregistration_evidence_sha256=frozen_load["sha256"],
            )


class _RiggedProvenance:
    """INVENTED: equal to nothing and unequal to nothing, so ``==`` and
    ``!=`` tests against the registered label both come out False."""

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return False

    __hash__ = object.__hash__


@pytest.mark.parametrize(
    "provenance",
    [_RiggedProvenance(), type("_Label", (str,), {})(ap.REGISTERED_REAL)],
    ids=["rigged-equality", "str-subclass"],
)
def test_a_registered_run_takes_only_an_exact_provenance_label(
    frozen_load, evidence, monkeypatch, provenance
):
    """A label that is not exactly one of the two registered strings is
    refused before anything else, so no comparison it rigs can skip the
    row-set guard while the registered checks still run."""

    import dataclasses

    altered = {
        **rows.REGISTERED_ROWS,
        "U0": dataclasses.replace(
            rows.REGISTERED_ROWS["U0"], income={"real_interest_rate": 0.02}
        ),
    }

    def reached(*args, **kwargs):
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", reached)
    with pytest.raises(runner.U2RunError, match="data_provenance"):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=provenance,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            row_set=altered,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )


class _MutatingProvenance(dict):
    """INVENTED: a provenance mapping that, when the parameter check reads
    it, adds an invented offset to one input frame in place and forges
    the seal over the result (review round 3: check, then use)."""

    def __init__(self, labels, act):
        super().__init__(labels)
        self._act = act

    # Overriding ``__iter__`` takes ``dict(...)`` off its fast path, so the
    # copy the parameter check makes calls ``keys``.
    def __iter__(self):
        self._act()
        return super().__iter__()

    def keys(self):
        self._act()
        return super().keys()


def _private_copy(rechecked: cohort.U2Inputs) -> cohort.U2Inputs:
    """The frozen load with its frames copied and its seal kept (equal
    frames, so the loader's seal still holds): a copy a test may edit."""

    import dataclasses

    income = {
        wave: frame.copy() for wave, frame in rechecked.family_income.items()
    }
    copy_ = dataclasses.replace(rechecked, family_income=income)
    object.__setattr__(copy_, "loader_seal", rechecked.loader_seal)
    return copy_


def test_frames_changed_after_the_check_reach_no_row(
    frozen_load, evidence, monkeypatch
):
    """Between the input check and the births, the run reads the caller's
    parameter provenance.  An edit made there to the caller's frames, with
    the seal forged again, reaches no row: the rows compute on the private
    snapshot the check rebuilt from the frozen frames' text (round 3,
    third pass; the second pass refused it at the births check)."""

    import dataclasses

    inputs = _private_copy(frozen_load["inputs"])
    fired = []

    def act():
        if fired:
            return
        fired.append(True)
        frame = inputs.family_income[2019]
        column = frame.columns.get_loc("total_family_income")
        frame.iat[0, column] = frame.iat[0, column] + _INVENTED_OFFSET
        seal = {
            **dict(inputs.loader_seal),
            "input_frames_sha256": cohort.input_frames_sha256(inputs),
        }
        object.__setattr__(inputs, "loader_seal", MappingProxyType(seal))

    pinned = parameters.committed_u2_parameters()
    params = dataclasses.replace(
        pinned,
        thresholds=dataclasses.replace(
            pinned.thresholds,
            provenance=_MutatingProvenance(pinned.thresholds.provenance, act),
        ),
    )

    seen = []

    def compute_row(row, row_inputs, *args, **kwargs):
        seen.append(row_inputs)
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            inputs,
            params,
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )
    assert fired == [True]
    assert (
        cohort.input_frames_sha256(inputs) != evidence["input_frames_sha256"]
    )
    (used,) = seen
    assert used is not inputs
    assert cohort.input_frames_sha256(used) == evidence["input_frames_sha256"]
    genuine = frozen_load["inputs"].family_income[2019]
    pd.testing.assert_series_equal(
        used.family_income[2019]["total_family_income"],
        genuine["total_family_income"].reset_index(drop=True),
    )


# ---------------------------------------------------------------------------
# Round 3, second pass: the frame digest and the evidence comparison must
# read exactly what the run computes on.  An independent adversarial
# verification of the first pass (four blind lanes, invented data) found
# that type confusion kept the digest and the seal intact while the rows
# read other values: a str subclass in the evidence record or bound hash,
# a dict subclass for a frame container, a str-subclass cell or column
# label, and a role context whose rules were rewritten after construction.
# INVENTED DATA - NOT A COMPARISON.
# ---------------------------------------------------------------------------
class _RiggedText(str):
    """INVENTED: prints as its text but equals everything and hashes as
    its text, so every comparison it makes comes out equal."""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = str.__hash__


class _ComparesAs(str):
    """INVENTED: prints (and so digests) as its own text but compares and
    hashes as ``other``."""

    def __new__(cls, text, other):
        value = super().__new__(cls, text)
        value._other = other
        return value

    def __eq__(self, other):
        return str(self._other) == other

    def __ne__(self, other):
        return str(self._other) != other

    def __hash__(self):
        return hash(str(self._other))


def test_a_rigged_digest_in_the_record_refuses(frozen_load, evidence):
    """Round 3, second pass: a record whose frame digest is a str subclass
    holding the frozen text (so it hashes to the bound value) but equal
    to everything no longer lets forged frames through."""

    rigged = {
        **evidence,
        "input_frames_sha256": _RiggedText(evidence["input_frames_sha256"]),
    }
    with pytest.raises(runner.U2RunError, match="not valid"):
        _registered_check(
            _income_forgery(frozen_load["inputs"]),
            frozen_load,
            preregistration_evidence=rigged,
        )


@pytest.mark.parametrize(
    "where",
    ["bound", "seal"],
)
def test_a_rigged_evidence_hash_refuses(frozen_load, evidence, where):
    """The bound hash and the seal's evidence hash must be exactly str:
    a subclass could compare equal to any other hash."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    sha = frozen_load["sha256"]
    if where == "bound":
        inputs, bound = rechecked, _RiggedText(sha)
    else:
        inputs, bound = dataclasses.replace(rechecked), sha
        seal = {**rechecked.loader_seal, cohort.EVIDENCE_KEY: _RiggedText(sha)}
        object.__setattr__(inputs, "loader_seal", MappingProxyType(seal))
        object.__setattr__(
            inputs,
            "provenance",
            {**rechecked.provenance, cohort.EVIDENCE_KEY: _RiggedText(sha)},
        )
    with pytest.raises(runner.U2RunError, match="exactly|64 lowercase hex"):
        runner.check_inputs(
            inputs,
            ap.REGISTERED_REAL,
            POINTER,
            sources.RoleContext.from_registry(),
            preregistration_evidence_sha256=bound,
            preregistration_evidence=evidence,
        )


def test_a_self_consistent_other_record_refuses_by_its_hash(
    frozen_load, evidence
):
    """Mutation check (round 3, second pass): a forged seal under the bound
    hash with a valid record describing the forged frames is refused by
    the record-hash comparison itself."""

    forged = _income_forgery(frozen_load["inputs"])
    other = loader.preregistration_evidence(forged)
    assert other["input_frames_sha256"] == cohort.input_frames_sha256(forged)
    with pytest.raises(runner.U2RunError, match="hashes to"):
        _registered_check(forged, frozen_load, preregistration_evidence=other)


_CONTAINERS = ("anchors", "family_income", "family_wealth", "employer_dc")
_LIES = ("get", "__getitem__", "items", "values", "__iter__", "keys")


def _two_faced(frames: dict, altered: dict, lie: str):
    """A dict subclass holding ``frames`` whose ``lie`` method serves
    ``altered`` instead (INVENTED)."""

    def method(self, *args, **kwargs):
        return getattr(dict, lie)(altered, *args, **kwargs)

    return type("_TwoFaced", (dict,), {lie: method})(frames)


@settings(max_examples=40, deadline=None)
@given(
    container=st.sampled_from(_CONTAINERS),
    lie=st.sampled_from(_LIES),
)
def test_no_frame_container_but_a_plain_dict_is_digested(
    frozen_load, evidence, container, lie
):
    """Invariant (round 3, second pass): the frame digest reads only plain
    dicts keyed by int, so a container that serves the digest one frame
    and the computation another is refused, whichever method lies; the
    registered check refuses it even with the loader's own seal copied."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    frames = getattr(rechecked, container)
    altered = {wave: frame.copy() for wave, frame in frames.items()}
    wave = sorted(altered)[0]
    column = altered[wave].select_dtypes("number").columns[0]
    altered[wave] = _offset_cell(altered[wave], column, 0, _INVENTED_OFFSET)
    lying = dataclasses.replace(
        rechecked, **{container: _two_faced(dict(frames), altered, lie)}
    )
    object.__setattr__(lying, "loader_seal", rechecked.loader_seal)
    with pytest.raises(cohort.U2CohortError, match="plain dict"):
        cohort.input_frames_sha256(lying)
    with pytest.raises(runner.U2RunError, match="plain dict"):
        _registered_check(
            lying, frozen_load, preregistration_evidence=evidence
        )


def test_a_wave_key_must_be_an_int(frozen_load):
    import dataclasses

    rechecked = frozen_load["inputs"]
    income = {float(wave): f for wave, f in rechecked.family_income.items()}
    with pytest.raises(cohort.U2CohortError, match="int"):
        cohort.input_frames_sha256(
            dataclasses.replace(rechecked, family_income=income)
        )


def _string_sites(inputs: cohort.U2Inputs) -> list[tuple]:
    """``(field, wave or None, column)`` of every string-valued column."""

    sites = []
    for name in _CONTAINERS:
        for wave, frame in sorted(getattr(inputs, name).items()):
            sites += [
                (name, wave, column)
                for column in frame.columns
                if frame[column].dtype == object
                or isinstance(frame[column].dtype, pd.StringDtype)
            ]
    for name in ("design", "persons", "marriage_history", "observed_earnings"):
        frame = getattr(inputs, name)
        sites += [
            (name, None, column)
            for column in frame.columns
            if frame[column].dtype == object
            or isinstance(frame[column].dtype, pd.StringDtype)
        ]
    return sites


def test_a_string_cell_that_compares_as_another_refuses(frozen_load, evidence):
    """The verification's minimized case: one ``how_ended`` cell keeps its
    text (and so the digest) but compares as ``separated``, edited in
    place with no seal forgery.  The digest now refuses any string cell
    that is not exactly a str."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    history = rechecked.marriage_history.copy()
    column = history.columns.get_loc("how_ended")
    text = history.iat[0, column]
    history.iat[0, column] = _ComparesAs(text, "separated")
    changed = dataclasses.replace(rechecked, marriage_history=history)
    object.__setattr__(changed, "loader_seal", rechecked.loader_seal)
    with pytest.raises(cohort.U2CohortError, match="exact str"):
        cohort.input_frames_sha256(changed)
    with pytest.raises(runner.U2RunError, match="exact str"):
        _registered_check(
            changed, frozen_load, preregistration_evidence=evidence
        )


@settings(max_examples=40, deadline=None)
@given(data=st.data())
def test_no_string_cell_but_an_exact_str_is_digested(frozen_load, data):
    """Invariant (round 3, second pass): for every string-valued column of
    every input frame and every row, a cell replaced by a str subclass of
    the same text (same CSV text, same dtype) is refused by the digest."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    name, wave, column = data.draw(
        st.sampled_from(_string_sites(rechecked)), label="site"
    )
    frames = getattr(rechecked, name)
    frame = (frames if wave is None else frames[wave]).copy()
    row = data.draw(st.integers(0, len(frame) - 1), label="row")
    position = frame.columns.get_loc(column)
    text = frame.iat[row, position]
    assume(type(text) is str)
    frame.iat[row, position] = _ComparesAs(text, text + "-invented")
    changed = dataclasses.replace(
        rechecked,
        **{name: frame if wave is None else {**frames, wave: frame}},
    )
    with pytest.raises(cohort.U2CohortError, match="exact str"):
        cohort.input_frames_sha256(changed)


def test_a_column_label_must_be_an_exact_str(frozen_load):
    """Two labels that print as each other's names would swap two columns'
    data under an unchanged digest; labels must be distinct exact str."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    persons = rechecked.persons.copy()
    persons.columns = [
        _ComparesAs(str(label), str(label)) for label in persons.columns
    ]
    with pytest.raises(cohort.U2CohortError, match="column labels"):
        cohort.input_frames_sha256(
            dataclasses.replace(rechecked, persons=persons)
        )


def test_an_unlisted_column_dtype_refuses(frozen_load):
    import dataclasses

    rechecked = frozen_load["inputs"]
    persons = rechecked.persons.assign(
        sex=rechecked.persons["sex"].astype("category")
    )
    with pytest.raises(cohort.U2CohortError, match="dtype"):
        cohort.input_frames_sha256(
            dataclasses.replace(rechecked, persons=persons)
        )


def test_the_loader_and_generator_frames_meet_the_type_rules(
    loaded, frozen_load, u2_inputs
):
    """The converse: the loader's own frames and the invented generator's
    pass the digest's type rules unchanged."""

    for inputs in (loaded["inputs"], frozen_load["inputs"], u2_inputs):
        cohort.input_frames_sha256(inputs)


def test_a_role_context_with_rewritten_rules_refuses(frozen_load, evidence):
    """A frozen RoleContext checks its rules only when built; rules
    rewritten afterwards (``object.__setattr__``) under the registry kind
    are refused by the registered check."""

    registry = sources.RoleContext.from_registry()
    object.__setattr__(
        registry,
        "rules",
        MappingProxyType(dict(sources.declared_role_rules())),
    )
    with pytest.raises(runner.U2RunError, match="role rules"):
        runner.check_inputs(
            frozen_load["inputs"],
            ap.REGISTERED_REAL,
            POINTER,
            registry,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )


def test_a_registered_run_computes_with_a_fresh_role_context(
    frozen_load, evidence, monkeypatch
):
    """Check, then use: the rows get a fresh committed role context, never
    the caller's object, so rules rewritten after the check (here from the
    progress callback) reach no row."""

    caller = sources.RoleContext.from_registry()
    seen = []

    def compute_row(row, inputs, params, births, *, role_context, **kwargs):
        seen.append(role_context)
        raise _Reached

    def progress(message):
        object.__setattr__(
            caller,
            "rules",
            MappingProxyType(dict(sources.declared_role_rules())),
        )

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=caller,
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
            progress=progress,
        )
    (used,) = seen
    assert used is not caller
    assert dict(used.rules) == dict(sources.RoleContext.from_registry().rules)


def test_the_inherited_readers_transforms_meet_the_type_rules(
    u2_inputs, monkeypatch
):
    """The loader reads marriage histories and observed earnings through
    U1's readers, which the other loader tests patch to return invented
    frames.  Here their own transforms run on INVENTED raw columns --
    ``marriage._build`` on raw MH codes, and ``family_earnings_panel``
    with the demographic panel and labor reader stubbed -- and the frames
    they build pass the digest's type rules (round 3 verification)."""

    import dataclasses

    codes = {
        "MH2": 700,  # INVENTED 1968 family numbers and person numbers
        "MH3": 1,
        "MH4": min(marriage._SEX),
        "MH5": 98,
        "MH6": 1950,
        "MH7": 701,
        "MH8": 2,
        "MH9": 1,
        "MH10": 6,
        "MH11": 1972,
        "MH12": min(marriage.HOW_ENDED),
        "MH13": 99,
        "MH14": 9999,
        "MH15": 99,
        "MH16": 9999,
        "MH17": 2021,
        "MH18": 1,
        "MH19": min(marriage.LAST_KNOWN_STATUS),
        "MH20": 1,
    }
    raw = pd.DataFrame([codes, {**codes, "MH3": 2, "MH7": 0, "MH8": 0}])
    history = marriage._build(raw)

    waves = (2013, 2015)
    head, spouse = family._relationship_codes(waves[0])
    demo = pd.DataFrame(
        {
            "person_id": [700001, 700002] * len(waves),
            "period": [wave for wave in waves for _ in range(2)],
            "interview": [1001, 1001, 2001, 2001],
            "relationship": [head[0], spouse[0]] * len(waves),
            "age": [63, 61, 65, 63],
            "weight": [1000.0, 1000.0, 1010.0, 1010.0],
        }
    )
    labor = pd.DataFrame(
        {
            "interview": [1001, 2001],
            "head_labor": [30_000, 31_000],
            "spouse_labor": [20_000, 0],
            "head_acc": [0, 1],
            "spouse_acc": [0, 0],
        }
    )
    monkeypatch.setattr(
        panels, "demographic_panel", lambda *, data_dir=None, max_period: demo
    )
    monkeypatch.setattr(
        family,
        "read_family_labor",
        lambda wave, data_dir=None: labor[
            labor["interview"] // 1000 == waves.index(wave) + 1
        ],
    )
    earnings = family.family_earnings_panel(waves=waves)
    assert set(earnings["role"]) == {"head", "spouse"}
    cohort.input_frames_sha256(
        dataclasses.replace(
            u2_inputs, marriage_history=history, observed_earnings=earnings
        )
    )


# ---------------------------------------------------------------------------
# Round 3, third pass: check, then use, for the frames.  A second adversarial
# round (three blind lanes) found that exact-type rules on pandas objects
# cannot close the class: an object in ``attrs`` runs code whenever pandas
# copies the frame, and an ExtensionArray subclass keeps the exact dtype
# and CSV text while the computation reads other values.  A registered run
# now computes only on frames parsed from the text the digest hashes, and
# records provenance from the bound record.  INVENTED DATA.
# ---------------------------------------------------------------------------
class _Hook:
    """INVENTED: runs ``act`` whenever pandas deep-copies a frame's attrs."""

    def __init__(self, act):
        self.act = act

    def __deepcopy__(self, memo):
        self.act()
        return "inert"


def _row_inputs(frozen_load, evidence, monkeypatch, inputs, **kwargs):
    """The inputs the first registered row receives (the row is stopped)."""

    seen = []

    def compute_row(row, row_inputs, *args, **kw):
        seen.append(row_inputs)
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            inputs,
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
            **kwargs,
        )
    (row_inputs,) = seen
    return row_inputs


def test_an_attrs_object_on_an_input_frame_refuses(frozen_load, evidence):
    """The verification's case: hooks in ``attrs`` that restore the frames
    before each digest and alter them after.  Any attrs entry refuses,
    before pandas copies anything."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    anchors = {w: f.copy() for w, f in rechecked.anchors.items()}
    fired = []
    anchors[2013].attrs["note"] = _Hook(lambda: fired.append(True))
    hooked = dataclasses.replace(rechecked, anchors=anchors)
    object.__setattr__(hooked, "loader_seal", rechecked.loader_seal)
    with pytest.raises(cohort.U2CohortError, match="attrs"):
        cohort.input_frames_sha256(hooked)
    with pytest.raises(runner.U2RunError, match="attrs"):
        _registered_check(
            hooked, frozen_load, preregistration_evidence=evidence
        )


class _SwapSexes(pd.arrays.StringArray):
    """INVENTED: a StringArray that keeps its text (so the digest) but
    reads male as female and female as male on scalar access."""

    def __getitem__(self, key):
        out = super().__getitem__(key)
        swap = {"male": "female", "female": "male"}
        return swap.get(out, out) if isinstance(out, str) else out


class _ShiftOnIteration(pd.arrays.IntegerArray):
    """INVENTED: an IntegerArray whose iteration adds 5."""

    def __iter__(self):
        for value in super().__iter__():
            yield value if value is pd.NA else value + _INVENTED_OFFSET


def _rigged_copy(rechecked):
    """The frozen load with two columns in place on rigged array classes
    (persons.sex, marriage_history.birth_year) and the loader's seal kept:
    the digest is unchanged."""

    import dataclasses

    persons = rechecked.persons.copy()
    history = rechecked.marriage_history.copy()
    sex = persons["sex"].astype("string").array
    persons["sex"] = pd.Series(
        _SwapSexes(sex._ndarray.copy()), index=persons.index
    )
    years = history["birth_year"].array
    history["birth_year"] = pd.Series(
        _ShiftOnIteration(years._data.copy(), years._mask.copy()),
        index=history.index,
    )
    rigged = dataclasses.replace(
        rechecked, persons=persons, marriage_history=history
    )
    object.__setattr__(rigged, "loader_seal", rechecked.loader_seal)
    return rigged


def test_rows_never_read_the_callers_arrays(
    frozen_load, evidence, monkeypatch
):
    """Rigged array classes behind exact dtypes keep the digest, but the
    rows receive the private snapshot: exact base arrays holding the
    frozen values, never the caller's objects."""

    rechecked = frozen_load["inputs"]
    rigged = _rigged_copy(rechecked)
    assert type(rigged.persons["sex"].array) is _SwapSexes
    used = _row_inputs(frozen_load, evidence, monkeypatch, rigged)
    assert used is not rigged
    assert cohort.input_frames_sha256(used) == evidence["input_frames_sha256"]
    sex = used.persons["sex"]
    assert type(sex.array) is not _SwapSexes
    assert list(sex) == list(rechecked.persons["sex"])
    years = used.marriage_history["birth_year"]
    assert type(years.array) is pd.arrays.IntegerArray
    assert list(years) == list(rechecked.marriage_history["birth_year"])


def test_the_snapshot_records_the_bound_records_provenance(
    frozen_load, evidence, monkeypatch
):
    """The rows' provenance comes from the bound record and the committed
    pins: the caller's in-place edits to its own provenance (registries,
    data directory) reach no row, and no data directory is recorded."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    edited = dataclasses.replace(
        rechecked,
        provenance={
            **rechecked.provenance,
            "registries": {"kind": "invented"},
            "psid_data_dir": "/invented/elsewhere",
        },
    )
    object.__setattr__(edited, "loader_seal", rechecked.loader_seal)
    used = _row_inputs(frozen_load, evidence, monkeypatch, edited)
    recorded = cohort._input_provenance(used)
    assert recorded["psid_files_sha256"] == evidence["psid_files_sha256"]
    assert recorded["psid_files_bundle_sha256"] == (
        evidence["psid_files_bundle_sha256"]
    )
    assert recorded[cohort.EVIDENCE_KEY] == frozen_load["sha256"]
    assert recorded["registries"] == (
        sources.RegistrySet.committed().provenance()
    )
    assert recorded["psid_data_dir"] is None
    assert recorded[cohort.SNAPSHOT_KEY] is True


@pytest.mark.parametrize(
    "where", ["psid_files_sha256", "cited_sources_sha256"]
)
def test_rigged_recorded_hashes_refuse(frozen_load, evidence, where):
    """The inputs' recorded hash maps must be plain dicts of exact str: a
    str subclass could compare equal to the frozen hashes."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    recorded = dict(rechecked.provenance[where])
    rigged = {key: _RiggedText("e" * 64) for key in recorded} or {
        "PSID/invented.sps": _RiggedText("e" * 64)
    }
    provenance = {**rechecked.provenance, where: rigged}
    seal = dict(rechecked.loader_seal)
    if where == "psid_files_sha256":
        # The bundle is rigged too, in the provenance and the seal, as the
        # verification's attack did, so only the exact-type rule refuses.
        bundle = _RiggedText(loader.files_bundle_sha256(rigged))
        provenance["psid_files_bundle_sha256"] = bundle
        seal["psid_files_bundle_sha256"] = bundle
    edited = dataclasses.replace(rechecked, provenance=provenance)
    object.__setattr__(edited, "loader_seal", MappingProxyType(seal))
    with pytest.raises(runner.U2RunError, match="plain dict of exact"):
        _registered_check(
            edited, frozen_load, preregistration_evidence=evidence
        )


@pytest.mark.parametrize(
    "where", ["psid_files_sha256", "cited_sources_sha256"]
)
def test_a_recorded_hash_map_must_be_exactly_a_dict(
    frozen_load, evidence, where
):
    """Closeout mutation lane b (mutant 9): a read-only proxy of the
    recorded map itself equals the frozen map, so only the plain-dict
    rule refuses it (INVENTED DATA - NOT A COMPARISON)."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    proxy = MappingProxyType(dict(rechecked.provenance[where]))
    assert proxy == evidence[where]
    edited = dataclasses.replace(
        rechecked, provenance={**rechecked.provenance, where: proxy}
    )
    object.__setattr__(edited, "loader_seal", rechecked.loader_seal)
    with pytest.raises(runner.U2RunError, match="plain dict of exact"):
        _registered_check(
            edited, frozen_load, preregistration_evidence=evidence
        )


def test_a_recorded_file_bundle_must_be_an_exact_str(frozen_load, evidence):
    """Closeout mutation lane b (mutant 10): the recorded file bundle must
    be exactly a str.  With the file hashes a plain dict of exact str, a
    str subclass that equals every value, written into the provenance and
    the seal (so the loader-seal check accepts it), would otherwise stand
    in for any other bundle (INVENTED DATA - NOT A COMPARISON)."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    assert type(rechecked.provenance["psid_files_sha256"]) is dict
    bundle = _RiggedText("0" * 64)
    forged = dataclasses.replace(
        rechecked,
        provenance={
            **rechecked.provenance,
            "psid_files_bundle_sha256": bundle,
        },
    )
    object.__setattr__(
        forged,
        "loader_seal",
        MappingProxyType(
            {**rechecked.loader_seal, "psid_files_bundle_sha256": bundle}
        ),
    )
    # The loader-seal check accepts it; only the exact-type rule refuses.
    cohort._input_provenance(forged)
    with pytest.raises(runner.U2RunError, match="PSID file hashes"):
        _registered_check(
            forged, frozen_load, preregistration_evidence=evidence
        )


class _TwoFacedProvenance(Mapping):
    """INVENTED: a provenance mapping whose ``[]`` (and so ``dict()``)
    serves ``served`` while its ``get`` serves ``honest``."""

    def __init__(self, honest, served):
        self._honest, self._served = dict(honest), dict(served)

    def __getitem__(self, key):
        return self._served[key]

    def __iter__(self):
        return iter(self._served)

    def __len__(self):
        return len(self._served)

    def get(self, key, default=None):
        return self._honest.get(key, default)


def test_the_snapshot_never_reads_the_callers_recorded_hashes(
    frozen_load, evidence, monkeypatch
):
    """Closeout mutation lane d (mutant 20): the snapshot's PSID file
    hashes, bundle and cited-source hashes are the bound record's, never
    the caller's.  A provenance mapping that serves the loader's hashes to
    the run's comparisons (``get``) and INVENTED ones to ``[]``, under a
    seal re-forged over the INVENTED bundle, passes every check; the run
    record and the rows must still carry the record's hashes."""

    import dataclasses

    rechecked = frozen_load["inputs"]
    honest = dict(rechecked.provenance)
    files = {key: "e" * 64 for key in honest["psid_files_sha256"]}
    bundle = loader.files_bundle_sha256(files)
    served = {
        **honest,
        "psid_files_sha256": files,
        "psid_files_bundle_sha256": bundle,
        "cited_sources_sha256": {"PSID/invented.sps": "e" * 64},
    }
    two_faced = dataclasses.replace(
        rechecked, provenance=_TwoFacedProvenance(honest, served)
    )
    seal = {**dict(rechecked.loader_seal), "psid_files_bundle_sha256": bundle}
    object.__setattr__(two_faced, "loader_seal", MappingProxyType(seal))
    result = runner.run_track_u2(
        two_faced,
        parameters.committed_u2_parameters(),
        data_provenance=ap.REGISTERED_REAL,
        role_context=sources.RoleContext.from_registry(),
        registration_pointer=POINTER,
        preregistration_evidence_sha256=frozen_load["sha256"],
        preregistration_evidence=evidence,
    )
    assert result["psid_files_sha256"] == evidence["psid_files_sha256"]
    assert result["cohort_provenance"]["psid_files_bundle_sha256"] == (
        evidence["psid_files_bundle_sha256"]
    )
    used = _row_inputs(frozen_load, evidence, monkeypatch, two_faced)
    assert dict(used.provenance["cited_sources_sha256"]) == (
        evidence["cited_sources_sha256"]
    )


def test_a_registered_run_takes_no_source_gate(frozen_load, evidence):
    gate = sources.SourceGate(
        sources.REGISTRY, sources.RegistrySet.committed()
    )
    gate.would_refuse["roles:2015.relationship.20"] = ["INVENTED"]
    with pytest.raises(runner.U2RunError, match="no source gate"):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=sources.RoleContext.from_registry(),
            registration_pointer=POINTER,
            source_gate=gate,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )


def test_a_registration_pointer_must_be_an_exact_str(frozen_load, evidence):
    pointer = type("_Pointer", (str,), {})(POINTER)
    with pytest.raises(runner.U2RunError, match="issue #42"):
        runner.check_inputs(
            frozen_load["inputs"],
            ap.REGISTERED_REAL,
            pointer,
            sources.RoleContext.from_registry(),
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )


def test_role_rules_are_final_and_bound_by_text():
    """RoleRule is final, and a RoleContext keeps the verified committed
    (or declared) rule objects, never the caller's: a rule whose field is
    a rigged str with the committed text is replaced by the committed
    one."""

    import dataclasses

    with pytest.raises(TypeError, match="final"):
        type("_Rule", (sources.RoleRule,), {})
    committed = dict(sources.RoleContext.from_registry().rules)
    rigged = {
        key: dataclasses.replace(
            rule,
            income_role=(
                None
                if rule.income_role is None
                else _RiggedText(rule.income_role)
            ),
        )
        for key, rule in committed.items()
    }
    context = sources.RoleContext(sources.REGISTRY, rigged)
    assert all(
        type(rule.income_role) in (str, type(None))
        for rule in context.rules.values()
    )
    assert sources.role_rules_text(context.rules) == (
        sources.role_rules_text(committed)
    )


def test_the_snapshot_rebuilds_the_loader_and_generator_frames_exactly(
    loaded, u2_inputs
):
    """The converse, and the invariant a legitimate registered run relies
    on: the loader's frames and the invented generator's rebuild from their
    digested text value for value, dtype for dtype, with the same digest."""

    for inputs in (loaded["inputs"], u2_inputs):
        rebuilt, digest = cohort.rebuilt_input_frames(inputs)
        assert digest == cohort.input_frames_sha256(inputs)
        for field, wave, _name, frame in cohort._digest_frames(inputs):
            copy = rebuilt[field] if wave is None else rebuilt[field][wave]
            pd.testing.assert_frame_equal(
                copy, frame.reset_index(drop=True), check_exact=True
            )


#: INVENTED text: printable characters, including the CSV delimiter,
#: quote and whitespace, without lone surrogates (which the digest refuses
#: as invalid Unicode) or control characters (a NUL does not survive the
#: CSV round trip, so a frame holding one refuses at the rebuild).
_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")),
    min_size=1,
    max_size=12,
)


@st.composite
def _frames(draw):
    """INVENTED frames over every allowed dtype, with missing values."""

    n = draw(st.integers(0, 6))
    columns = {}
    kinds = draw(
        st.lists(
            st.sampled_from(
                (
                    "int64",
                    "float64",
                    "bool",
                    "Int64",
                    "str",
                    "string",
                    "object",
                )
            ),
            min_size=1,
            max_size=6,
        )
    )
    for index, kind in enumerate(kinds):
        name = f"c{index}"
        if kind == "int64":
            values = draw(
                st.lists(st.integers(-(2**62), 2**62), min_size=n, max_size=n)
            )
        elif kind == "float64":
            values = draw(
                st.lists(
                    st.floats(allow_nan=True, allow_infinity=True, width=64),
                    min_size=n,
                    max_size=n,
                )
            )
        elif kind == "bool":
            values = draw(st.lists(st.booleans(), min_size=n, max_size=n))
        elif kind == "Int64":
            values = draw(
                st.lists(
                    st.none() | st.integers(-(2**62), 2**62),
                    min_size=n,
                    max_size=n,
                )
            )
        elif kind == "object":
            # An object column's missing cells are NaN (round 3: None or
            # pd.NA would rebuild as NaN, so the type rules refuse them).
            values = draw(
                st.lists(st.just(math.nan) | _TEXT, min_size=n, max_size=n)
            )
        else:
            values = draw(st.lists(st.none() | _TEXT, min_size=n, max_size=n))
        if kind == "float64":
            columns[name] = np.array(values, dtype="float64")
        elif kind == "object":
            columns[name] = np.array(values, dtype=object)
        else:
            columns[name] = pd.array(values, dtype=kind)
    return pd.DataFrame(columns)


def _one_text_cell(text, dtype):
    """An INVENTED one-column frame holding one text cell."""

    if dtype == "object":
        return pd.DataFrame({"c0": np.array([text], dtype=object)})
    return pd.DataFrame({"c0": pd.array([text], dtype=dtype)})


@settings(max_examples=300, deadline=None)
@given(frame=_frames())
# The closeout review's minimized counterexample: a one-column frame
# whose only text cell is whitespace writes a whitespace-only CSV line,
# which pandas' default parser drops (finding 3).
@example(frame=_one_text_cell(" ", "str"))
@example(frame=_one_text_cell("\u3000", "string"))
@example(frame=_one_text_cell(" ", "object"))
def test_every_frame_over_the_allowed_dtypes_rebuilds_exactly(frame):
    """Invariant (round 3): every frame built from base types over the
    allowed dtypes -- full-precision floats, NaN, infinities, missing
    values, text with delimiters, quotes and whitespace, object columns
    of text and NaN -- is accepted by the type rules and rebuilds from
    its digested text to the same values and dtypes.  No refusal passes:
    a refusal here would be a false refusal of a legitimate frame at
    step 4 (the third round of verification found pandas' default float
    parser misreading 16-17 digit reprs; the closeout review, a dropped
    whitespace-only line)."""

    text = cohort._frame_text("invented", frame)
    rebuilt = cohort._rebuild_frame("invented", text)
    pd.testing.assert_frame_equal(rebuilt, frame, check_exact=True)
    assert cohort._frame_text("invented", rebuilt) == text


@pytest.mark.parametrize("dtype", ["str", "string", "object"])
@pytest.mark.parametrize("text", [" ", "\t", "\u3000", " \t "])
def test_a_whitespace_only_text_cell_rebuilds(text, dtype):
    """The closeout review's finding 3 (INVENTED cells): a one-column
    frame holding a whitespace-only cell writes a whitespace-only CSV
    line.  The rebuild keeps blank lines as rows, so the frame rebuilds
    exactly instead of being falsely refused at step 4."""

    frame = _one_text_cell(text, dtype)
    rebuilt = cohort._rebuild_frame(
        "invented", cohort._frame_text("invented", frame)
    )
    pd.testing.assert_frame_equal(rebuilt, frame, check_exact=True)


def test_computed_floats_rebuild_exactly():
    """The verification's case: a weight computed as 0.013 * 8950792
    (INVENTED) writes a 17-digit repr that the default parser misreads."""

    frame = pd.DataFrame(
        {"weight": np.array([0.013 * 8_950_792, 0.1 + 0.2, 1 / 3])}
    )
    rebuilt = cohort._rebuild_frame(
        "invented", cohort._frame_text("invented", frame)
    )
    pd.testing.assert_frame_equal(rebuilt, frame, check_exact=True)


def test_role_contexts_hold_private_rule_objects():
    """Round 3: each RoleContext holds its own copies of the committed
    rules, so an in-place edit of one context's (frozen) RoleRule cannot
    reach another context -- a registered run's fresh one included."""

    first = sources.RoleContext.from_registry()
    second = sources.RoleContext.from_registry()
    assert {id(rule) for rule in first.rules.values()}.isdisjoint(
        id(rule) for rule in second.rules.values()
    )
    committed = sources.role_rules_text(second.rules)
    rule = first.rules[(2015, 20)]
    object.__setattr__(rule, "refusal", None)  # INVENTED edit in place
    assert sources.role_rules_text(second.rules) == committed
    assert (
        sources.role_rules_text(sources.RoleContext.from_registry().rules)
        == committed
    )


def test_role_contexts_hold_private_exclusion_objects():
    """Closeout review, finding 4: a context's rules hold their own
    FamilyUnitExclusion objects (``RoleRule(**rule.as_dict())`` rebuilds
    them), shared with no other context, the cached committed rules, the
    declared table or the module's two exclusions.  So an in-place edit
    of one context's exclusion reaches no other context -- a registered
    run's fresh one included."""

    def exclusions(rules):
        return {
            id(rule.family_unit_exclusion)
            for rule in rules.values()
            if rule.family_unit_exclusion is not None
        }

    first = sources.RoleContext.from_registry()
    second = sources.RoleContext.from_registry()
    held = exclusions(first.rules)
    assert held  # section 16c's exclusions are attached
    for other in (
        second.rules,
        sources.RoleContext.declared().rules,
        sources._committed_role_rules(),
        sources.declared_role_rules(),
    ):
        assert held.isdisjoint(exclusions(other))
    assert held.isdisjoint(
        {id(sources._B1_EXCLUSION), id(sources._B2_EXCLUSION)}
    )
    committed = sources.role_rules_text(second.rules)
    exclusion = first.rules[(2015, 20)].family_unit_exclusion
    object.__setattr__(exclusion, "sex", None)  # INVENTED edit in place
    assert sources.role_rules_text(first.rules) != committed
    assert sources.role_rules_text(second.rules) == committed
    assert (
        sources.role_rules_text(sources.RoleContext.from_registry().rules)
        == committed
    )


def _checked_context(frozen_load, evidence, context):
    return runner.check_inputs(
        frozen_load["inputs"],
        ap.REGISTERED_REAL,
        POINTER,
        context,
        preregistration_evidence_sha256=frozen_load["sha256"],
        preregistration_evidence=evidence,
    )


class _LookalikeRule:
    """INVENTED: not a RoleRule, but writes a committed rule's as_dict()
    and reports no refusal, whatever the rule it copies says."""

    refusal = None

    def __init__(self, rule):
        self._rule = rule

    def as_dict(self):
        return self._rule.as_dict()


def test_a_lookalike_rule_context_refuses(frozen_load, evidence):
    """Closeout mutation lane c (mutant 16): rules written into a context
    after construction must each be exactly a RoleRule, even when they
    write the committed rules' text (INVENTED DATA - NOT A COMPARISON)."""

    registry = sources.RoleContext.from_registry()
    lookalikes = {
        key: _LookalikeRule(rule) for key, rule in registry.rules.items()
    }
    with pytest.raises(sources.U2SourceRefusal, match="exactly a RoleRule"):
        sources.role_rules_text(lookalikes)
    with pytest.raises(sources.U2SourceRefusal, match="exactly a RoleRule"):
        sources.RoleContext(sources.REGISTRY, lookalikes)
    object.__setattr__(registry, "rules", MappingProxyType(lookalikes))
    with pytest.raises(runner.U2RunError, match="exactly a RoleRule"):
        _checked_context(frozen_load, evidence, registry)


def test_rewritten_rules_with_a_rigged_field_refuse(frozen_load, evidence):
    """Closeout mutation lane c (mutant 27): every income role rewritten,
    after construction, to an INVENTED rigged str of "head" -- equal to
    everything, so ``==`` on the rules would pass -- is refused, because
    the check compares the rules' text."""

    import dataclasses

    registry = sources.RoleContext.from_registry()
    rigged = {
        key: dataclasses.replace(
            rule,
            income_role=(
                None if rule.income_role is None else _RiggedText("head")
            ),
        )
        for key, rule in registry.rules.items()
    }
    object.__setattr__(registry, "rules", MappingProxyType(rigged))
    with pytest.raises(runner.U2RunError, match="role rules"):
        _checked_context(frozen_load, evidence, registry)


class _ExclusionLookalike:
    """INVENTED: prints as the committed B1 exclusion but applies to
    nobody."""

    def __init__(self, exclusion):
        self.disposition, self.sex = exclusion.disposition, exclusion.sex

    def applies(self, sex):
        return False

    def as_dict(self):
        return {"disposition": self.disposition, "sex": self.sex}


def test_a_rule_holds_exactly_a_family_unit_exclusion(frozen_load, evidence):
    """Closeout mutation lane c: the exclusion a rule holds must be
    exactly a FamilyUnitExclusion.  The class is final, and an object
    written into a rule after construction that prints as the committed
    exclusion but applies to nobody is refused by the registered check
    (INVENTED DATA - NOT A COMPARISON)."""

    with pytest.raises(TypeError, match="final"):
        type("_Exclusion", (sources.FamilyUnitExclusion,), {})
    caller = sources.RoleContext.from_registry()
    rule = caller.rules[(2015, 20)]
    swapped = _ExclusionLookalike(rule.family_unit_exclusion)
    object.__setattr__(rule, "family_unit_exclusion", swapped)
    assert not caller.rule(2015, 20).family_unit_exclusion.applies("male")
    assert rule.as_dict() == (
        sources.RoleContext.from_registry().rules[(2015, 20)].as_dict()
    )
    with pytest.raises(sources.U2SourceRefusal, match="FamilyUnitExclusion"):
        sources.role_rules_text(caller.rules)
    with pytest.raises(runner.U2RunError, match="FamilyUnitExclusion"):
        _checked_context(frozen_load, evidence, caller)


def _exclusions(context):
    return [
        rule.family_unit_exclusion
        for rule in context.rules.values()
        if rule.family_unit_exclusion is not None
    ]


def test_exclusions_edited_from_the_callback_reach_no_row(
    frozen_load, evidence, monkeypatch
):
    """Closeout mutation lane c (mutant 29): the progress callback edits
    the passed context's exclusions in place after the run built its
    fresh context; the rows' rules are still the committed ones (INVENTED
    edit)."""

    caller = sources.RoleContext.from_registry()
    committed = sources.role_rules_text(caller.rules)
    edited = _exclusions(caller)
    assert edited
    seen = []

    def progress(message):
        for exclusion in edited:
            object.__setattr__(exclusion, "sex", "female")  # INVENTED edit

    def compute_row(row, inputs, params, births, *, role_context, **kwargs):
        seen.append(sources.role_rules_text(role_context.rules))
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=caller,
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
            progress=progress,
        )
    assert sources.role_rules_text(caller.rules) != committed
    assert seen == [committed]


def test_rules_edited_in_place_from_the_callback_reach_no_row(
    frozen_load, evidence, monkeypatch
):
    """The verification's case: the progress callback edits the passed
    context's RoleRule objects in place, after the run built its fresh
    context.  The rows' rules are still the committed ones."""

    caller = sources.RoleContext.from_registry()
    committed = sources.role_rules_text(caller.rules)
    seen = []

    def progress(message):
        for rule in caller.rules.values():
            object.__setattr__(rule, "refusal", None)  # INVENTED edit

    def compute_row(row, inputs, params, births, *, role_context, **kwargs):
        seen.append(sources.role_rules_text(role_context.rules))
        raise _Reached

    monkeypatch.setattr(runner, "_compute_row", compute_row)
    with pytest.raises(_Reached):
        runner.run_track_u2(
            frozen_load["inputs"],
            parameters.committed_u2_parameters(),
            data_provenance=ap.REGISTERED_REAL,
            role_context=caller,
            registration_pointer=POINTER,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
            progress=progress,
        )
    assert sources.role_rules_text(caller.rules) != committed
    assert seen == [committed]


def test_no_evidence_is_recorded_from_a_registered_snapshot(
    frozen_load, evidence, monkeypatch
):
    """The snapshot is private and marked: the step-4 evidence writer
    refuses it, and cohort exports no function that mints one."""

    assert not hasattr(cohort, "registered_snapshot")
    used = _row_inputs(
        frozen_load, evidence, monkeypatch, frozen_load["inputs"]
    )
    assert cohort._input_provenance(used)[cohort.SNAPSHOT_KEY] is True
    with pytest.raises(loader.U2LoaderRefusal, match="snapshot"):
        loader.preregistration_evidence(used)


def test_an_object_column_holds_only_nan_as_missing(u2_inputs):
    """None or pd.NA in an object column would rebuild as NaN: refused, so
    a rebuild gives back exactly the same values."""

    import dataclasses

    for marker in (None, pd.NA):
        persons = u2_inputs.persons.assign(
            sex=pd.Series(
                list(u2_inputs.persons["sex"].iloc[:-1]) + [marker],
                dtype=object,
            )
        )
        with pytest.raises(cohort.U2CohortError, match="NaN"):
            cohort.input_frames_sha256(
                dataclasses.replace(u2_inputs, persons=persons)
            )


def test_invalid_unicode_refuses_as_a_cohort_error(u2_inputs):
    import dataclasses

    persons = u2_inputs.persons.copy()
    persons.iloc[0, persons.columns.get_loc("sex")] = "x\ud800"
    with pytest.raises(cohort.U2CohortError, match="Unicode"):
        cohort.input_frames_sha256(
            dataclasses.replace(u2_inputs, persons=persons)
        )


def test_a_role_registry_refusal_is_a_run_error(
    frozen_load, evidence, monkeypatch
):
    def refuse(*args, **kwargs):
        raise sources.U2SourceRefusal("INVENTED refusal")

    registry = sources.RoleContext.from_registry()
    monkeypatch.setattr(sources.RoleContext, "from_registry", refuse)
    with pytest.raises(runner.U2RunError, match="INVENTED refusal"):
        runner.check_inputs(
            frozen_load["inputs"],
            ap.REGISTERED_REAL,
            POINTER,
            registry,
            preregistration_evidence_sha256=frozen_load["sha256"],
            preregistration_evidence=evidence,
        )


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda f: f.assign(sex=f["sex"].astype("category")), "dtype"),
        (lambda f: f.assign(extra=np.arange(len(f), dtype="int32")), "dtype"),
        (
            lambda f: f.assign(
                sex=pd.Series(
                    list(f["sex"].iloc[:-1]) + [""], dtype=f["sex"].dtype
                )
            ),
            "nonempty",
        ),
        (
            lambda f: f.assign(
                sex=pd.Series(list(f["sex"].iloc[:-1]) + [1.5], dtype=object)
            ),
            "float",
        ),
        (
            lambda f: f.assign(
                sex=pd.Series(
                    list(f["sex"].iloc[:-1])
                    + [type("_S", (str,), {})("male")],
                    dtype=object,
                )
            ),
            "exact str",
        ),
        (
            lambda f: f.set_axis(["person_id", "person_id"], axis=1),
            "column labels",
        ),
        (
            lambda f: f.set_axis(
                type("_Index", (pd.Index,), {})._simple_new(
                    f.columns._values, name=None
                ),
                axis=1,
            ),
            "column labels",
        ),
        (
            lambda f: f.assign(
                sex=f["sex"].astype(type("_Dtype", (pd.StringDtype,), {})())
            ),
            "dtype",
        ),
        # Closeout mutation lane a: a non-native byte order keeps the
        # dtype's name ("int64") but the digest writes ">i8", which no
        # snapshot parses.
        (
            lambda f: f.assign(
                person_id=f["person_id"].to_numpy().astype(">i8")
            ),
            "dtype",
        ),
        (
            lambda f: f.assign(
                person_id=f["person_id"].to_numpy().astype(">f8")
            ),
            "dtype",
        ),
    ],
    ids=[
        "category",
        "int32",
        "empty-string",
        "object-float",
        "object-str-subclass",
        "duplicate-labels",
        "index-subclass",
        "dtype-subclass",
        "big-endian-int64",
        "big-endian-float64",
    ],
)
def test_the_type_rules_refuse_each_case(u2_inputs, change, message):
    """Each clause of the digest's type rules, including those the
    verification's mutants showed untested (index, dtype and int-subclass
    cases, duplicate labels, the object-column branch)."""

    import dataclasses

    try:
        persons = change(u2_inputs.persons.copy())
    except (TypeError, ValueError):
        pytest.skip("pandas does not build this frame")
    with pytest.raises(cohort.U2CohortError, match=message):
        cohort.input_frames_sha256(
            dataclasses.replace(u2_inputs, persons=persons)
        )


@pytest.mark.parametrize("key", ["int-subclass", "bool"])
def test_a_wave_key_must_be_exactly_int(u2_inputs, key):
    import dataclasses

    wave_type = type("_Wave", (int,), {}) if key == "int-subclass" else bool
    frames = u2_inputs.family_income
    first = sorted(frames)[0]
    income = {
        wave_type(first): frames[first],
        **{wave: frame for wave, frame in frames.items() if wave != first},
    }
    with pytest.raises(cohort.U2CohortError, match="int"):
        cohort.input_frames_sha256(
            dataclasses.replace(u2_inputs, family_income=income)
        )


def test_the_step_4_evidence_refuses_frames_that_do_not_rebuild(loaded):
    """Fail early: a frame whose text does not parse back to itself (here
    an INVENTED column with an empty label, which the CSV reader renames)
    passes the type rules but refuses at the evidence writer, before
    registration."""

    import dataclasses

    rechecked = loaded["inputs"]
    persons = rechecked.persons.assign(**{"": 0})
    changed = dataclasses.replace(rechecked, persons=persons)
    cohort.input_frames_sha256(changed)
    seal = {
        **dict(rechecked.loader_seal),
        "input_frames_sha256": cohort.input_frames_sha256(changed),
    }
    object.__setattr__(changed, "loader_seal", MappingProxyType(seal))
    with pytest.raises(loader.U2LoaderRefusal, match="rebuild"):
        loader.preregistration_evidence(changed)
