"""The registered U2 loader's stages 2 and 3 on an invented staged
directory (section 14; review finding 6 of the u2m2 review).

INVENTED DATA - NOT A COMPARISON.  At the adjudicated registries the
loader refuses in stage 1, before any PSID file is opened
(``test_u2_mappings.py``).  To execute the rest of it before any real
record is read, this module stages the invented population as PSID-shaped
fixed-width files -- one family file and setup per support wave, written
at the registry layouts, and an individual file and setup -- in a
temporary directory and runs :func:`loader.load_u2_inputs` against it
with four patches, each named where it is applied:

* ``sources.blockers`` returns no blocker, so stage 1 and the registry
  gate pass (the registry's own routes, not the declared ones, are
  applied);
* ``loader.check_source_hashes`` returns nothing, because the registries
  cite the real PSID setup files and codebooks, which are not staged
  here (the rehash itself is tested in ``test_u2_mappings.py``);
* the inherited marriage-history and earnings readers return the
  invented frames.

An audit hook refuses any open under the PSID directory -- the default
one and the one under the account's real home, which differ when HOME is
overridden -- for the duration of each load.  Everything else -- path
resolution, the setup cross-checks, the fixed-width reads, the file
hashes and the seal -- is the code a registered run executes.
"""

from __future__ import annotations

import os
import pwd
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from populace_dynamics.data import family, marriage, psid
from populace_dynamics.estimates import adjusted_poverty as ap
from populace_dynamics.uniform_cut_track_u2 import (
    cohort,
    invented,
    loader,
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


def _load(root, inputs: cohort.U2Inputs) -> cohort.U2Inputs:
    """Run the real loader on ``root`` with the four named patches."""

    # The committed role rules are cached on first use; compute them
    # before ``blockers`` is patched so the cache holds the real rules.
    sources.RoleContext.from_registry()
    patch = pytest.MonkeyPatch()
    try:
        patch.setattr(sources, "blockers", lambda entry, name: [])
        patch.setattr(
            loader, "check_source_hashes", lambda registries, data_dir: {}
        )
        patch.setattr(
            marriage,
            "marriage_history",
            lambda *, data_dir=None, nrows=None: inputs.marriage_history,
        )
        patch.setattr(
            family,
            "family_earnings_panel",
            lambda *, waves=None, data_dir=None: inputs.observed_earnings,
        )
        _GUARD["active"], _GUARD["opened"] = True, []
        return loader.load_u2_inputs(data_dir=root)
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


def test_loaded_inputs_take_the_registered_path_only(loaded, declared):
    """Sealed psid_files inputs: the registered guard accepts them, the
    declared role context refuses them, and the committed roles registry
    refuses the build on the refused codes (2015 code 20 among them)."""

    inputs = loaded["inputs"]
    registry = sources.RoleContext.from_registry()
    assert (
        runner.check_inputs(inputs, ap.REGISTERED_REAL, POINTER, registry)
        == {}
    )
    with pytest.raises(runner.U2RunError, match="invented"):
        runner.check_inputs(inputs, ap.INVENTED, None, registry)
    with pytest.raises(cohort.U2CohortError, match="invented inputs"):
        cohort.build_u2_cohort(inputs, role_context=declared)
    with pytest.raises(sources.U2RoleRefusal):
        cohort.build_u2_cohort(inputs, role_context=registry)


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
