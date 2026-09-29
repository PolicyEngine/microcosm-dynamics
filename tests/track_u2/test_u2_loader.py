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
