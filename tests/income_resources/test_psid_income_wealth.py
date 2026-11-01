"""Invented records only; these fixtures contain no survey observations.

The invented setup retains registry column specifications, which the
separate metadata integration suite checks against staged setup files.
"""

import hashlib
from io import StringIO

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from populace_dynamics.data import family_income
from populace_dynamics.data import psid_income_wealth as reader

INVENTED_SETTINGS = settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def invented_setup(wave, tmp_path, monkeypatch):
    """Pin an invented setup retaining the real registry's column positions."""

    registry = reader.REGISTRY[wave]
    items = {**registry["income"], **registry.get("wealth", {})}
    by_variable = {item["variable"]: item for item in items.values()}
    lines = ["DATA LIST FILE = PSID FIXED /"]
    lines.extend(
        f'  {variable} {item["start"]} - {item["end"]}'
        for variable, item in by_variable.items()
    )
    lines.extend([".", "VARIABLE LABELS"])
    lines.extend(
        f'  {variable} "{item["label"]}"'
        for variable, item in by_variable.items()
    )
    lines.extend([".", ""])
    path = tmp_path / f"INVENTED_FAMILY_{wave}.sps"
    path.write_text("\n".join(lines))
    monkeypatch.setitem(
        reader.REGISTRY[wave]["setup"],
        "sha256",
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    return path


def invented_value(concept, item):
    if concept == "interview":
        return 1
    if concept in ("head_age", "wife_age"):
        return 45
    if item.get("allowed_codes") is not None:
        return item["allowed_codes"][0]
    if "valid_ranges" in item:
        for low, high in item["valid_ranges"]:
            if low <= 0 <= high:
                return 0
        return item["valid_ranges"][0][0]
    return max(0, item.get("valid_min", 0))


def invented_records(wave, records):
    registry = reader.REGISTRY[wave]
    items = {**registry["income"], **registry.get("wealth", {})}
    width = max(item["end"] for item in items.values())
    lines = []
    for overrides in records:
        line = [" "] * width
        for concept, item in items.items():
            value = overrides.get(concept, invented_value(concept, item))
            decimals = item.get("decimals", 0)
            token = "" if value is None else f"{value:.{decimals}f}"
            length = item["end"] - item["start"] + 1
            assert len(token) <= length, (concept, token, length)
            line[item["start"] - 1 : item["end"]] = token.rjust(length)
        lines.append("".join(line))
    return StringIO("\n".join(lines) + ("\n" if lines else ""))


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
def test_registry_is_detached_and_complete(wave):
    registry = reader.wave_registry(wave)
    registry["income"].clear()
    assert reader.income_variables(wave)
    for concept, item in reader.wave_registry(wave)["income"].items():
        assert item["variable"] and item["label"]
        assert item["codebook_page"]
        assert item["start"] <= item["end"]
        assert reader.income_variables(wave)[concept] == (
            item["variable"],
            item["label"],
        )


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
def test_income_extraction_and_dtypes(wave, tmp_path, monkeypatch):
    path = invented_setup(wave, tmp_path, monkeypatch)
    values = {"interview": 17, "head_labor": 12345}
    frame = reader.read_family_income(
        wave, setup_path=path, records_path=invented_records(wave, [values])
    )
    assert frame["interview"].tolist() == [17]
    assert frame["head_labor"].tolist() == [12345]
    assert str(frame["head_labor"].dtype) in ("int64", "Int64")
    assert str(frame["head_age"].dtype) == "Int64"
    assert str(frame["head_sex"].dtype) == "string"
    assert frame["income_year"].tolist() == [wave - 1]


@pytest.mark.parametrize("wave", reader.WEALTH_WAVES)
def test_wealth_extraction_and_all_accuracy_flags(wave, tmp_path, monkeypatch):
    path = invented_setup(wave, tmp_path, monkeypatch)
    frame = reader.read_family_wealth(
        wave,
        setup_path=path,
        records_path=invented_records(wave, [{"wealth1": -12345}]),
    )
    assert frame["wealth1"].tolist() == [-12345]
    for concept in reader.wealth_variables(wave):
        assert concept in frame
    for concept in reader.wave_registry(wave)["wealth"]:
        if concept.endswith("_acc"):
            assert str(frame[concept].dtype) == "int64"


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
def test_documented_missing_and_top_codes(wave, tmp_path, monkeypatch):
    path = invented_setup(wave, tmp_path, monkeypatch)
    table = reader.wave_registry(wave)["income"]
    for concept, item in table.items():
        for code in item.get("missing_codes", []):
            if concept == "interview":
                continue
            frame = reader.read_family_income(
                wave,
                setup_path=path,
                records_path=invented_records(wave, [{concept: code}]),
                concepts=[concept],
            )
            assert pd.isna(frame.loc[0, concept])
        for code in item.get("top_codes", []):
            frame = reader.read_family_income(
                wave,
                setup_path=path,
                records_path=invented_records(wave, [{concept: code}]),
                concepts=[concept],
            )
            assert frame.loc[0, concept] == code


@pytest.mark.parametrize(
    ("wave", "kind"),
    [
        *((w, "income") for w in reader.INCOME_WAVES),
        *((w, "wealth") for w in reader.WEALTH_WAVES),
    ],
)
@INVENTED_SETTINGS
@given(ids=st.lists(st.integers(1, 6000), unique=True, max_size=15))
def test_never_drops_or_duplicates_a_family(
    ids, wave, kind, tmp_path, monkeypatch
):
    path = invented_setup(wave, tmp_path, monkeypatch)
    function = getattr(reader, f"read_family_{kind}")
    frame = function(
        wave,
        setup_path=path,
        records_path=invented_records(wave, [{"interview": i} for i in ids]),
        concepts=["head_labor" if kind == "income" else "wealth1"],
    )
    assert frame["interview"].tolist() == ids
    assert len(frame) == len(ids)


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
@INVENTED_SETTINGS
@given(data=st.data())
def test_income_aggregate_identities(data, wave, tmp_path, monkeypatch):
    path = invented_setup(wave, tmp_path, monkeypatch)
    registry = reader.wave_registry(wave)
    identities = registry["income_identities"]
    values = {
        component: data.draw(st.integers(0, 1000), label=component)
        for components in identities.values()
        for component in components
        if component not in identities
    }
    pending = dict(identities)
    while pending:
        ready = [
            aggregate
            for aggregate, components in pending.items()
            if all(component in values for component in components)
        ]
        assert ready, "Cyclic income definitions"
        for aggregate in ready:
            values[aggregate] = sum(values[c] for c in pending.pop(aggregate))
    frame = reader.read_family_income(
        wave, setup_path=path, records_path=invented_records(wave, [values])
    )
    result = reader.reconcile_family_income(frame)[str(wave)]
    assert result
    assert all(counts["n_exact"] == 1 for counts in result.values())
    for aggregate in identities:
        frame[aggregate] += reader.RECONCILIATION_TOLERANCE
        counts = reader.reconcile_family_income(frame)[str(wave)][aggregate]
        assert counts["n_within_tolerance"] == 1
        frame[aggregate] += 1
        counts = reader.reconcile_family_income(frame)[str(wave)][aggregate]
        assert counts["n_beyond_tolerance"] == 1
        frame[aggregate] -= reader.RECONCILIATION_TOLERANCE + 1


@pytest.mark.parametrize("wave", reader.WEALTH_WAVES)
@INVENTED_SETTINGS
@given(values=st.lists(st.integers(0, 100_000), min_size=20, max_size=20))
def test_exact_wealth_identities(values, wave, tmp_path, monkeypatch):
    path = invented_setup(wave, tmp_path, monkeypatch)
    registry = reader.wave_registry(wave)
    components = [*registry["wealth_assets"], *registry["wealth_debts"]]
    record = dict(zip(components, values, strict=False))
    record["wealth1"] = sum(record[c] for c in registry["wealth_assets"])
    record["wealth1"] -= sum(record[c] for c in registry["wealth_debts"])
    record["home_equity"] = values[-1] - values[-2]
    record["wealth2"] = record["wealth1"] + record["home_equity"]
    frame = reader.read_family_wealth(
        wave, setup_path=path, records_path=invented_records(wave, [record])
    )
    result = reader.reconcile_wealth1(frame)[str(wave)]
    assert result["wealth1"]["n_exact"] == 1
    assert result["wealth2"]["n_exact"] == 1


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
@INVENTED_SETTINGS
@given(code=st.integers(0, 9))
def test_unverified_accuracy_code_always_raises(
    code, wave, tmp_path, monkeypatch
):
    path = invented_setup(wave, tmp_path, monkeypatch)
    registry = reader.wave_registry(wave)
    for kind in ("income", "wealth"):
        table = registry.get(kind, {})
        for concept, item in table.items():
            if not concept.endswith("_acc"):
                continue
            if code in item["allowed_codes"] or code in item.get(
                "missing_codes", []
            ):
                continue
            function = getattr(reader, f"read_family_{kind}")
            with pytest.raises(reader.UnverifiedMetadataError, match=concept):
                function(
                    wave,
                    setup_path=path,
                    records_path=invented_records(wave, [{concept: code}]),
                    concepts=[concept],
                )


def test_refuses_unpinned_setup_before_opening_records(tmp_path):
    path = tmp_path / "INVENTED_UNPINNED.sps"
    path.write_text("DATA LIST FILE = PSID FIXED /\n ER1 1 - 1\n.\n")
    with pytest.raises(reader.UnverifiedMetadataError, match="Unpinned"):
        reader.read_family_income(
            2023, setup_path=path, records_path=tmp_path / "DOES_NOT_EXIST"
        )


@INVENTED_SETTINGS
@given(st.integers().filter(lambda wave: wave not in reader.INCOME_WAVES))
def test_uncovered_wave_always_raises(wave):
    with pytest.raises(reader.UnverifiedMetadataError):
        reader.income_variables(wave)


@INVENTED_SETTINGS
@given(st.text(min_size=1).map(lambda text: "INVENTED_UNKNOWN_" + text))
def test_uncovered_concept_always_raises(concept):
    with pytest.raises(reader.UnverifiedMetadataError, match="concept"):
        reader.read_family_income(
            2023,
            setup_path="unused.sps",
            records_path="unused",
            concepts=[concept],
        )


@pytest.mark.parametrize("overrides", [{"interview": 0}, {"interview": 1}])
def test_refuses_nonpositive_or_duplicate_id(overrides, tmp_path, monkeypatch):
    path = invented_setup(2023, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="interview"):
        reader.read_family_income(
            2023,
            setup_path=path,
            records_path=invented_records(2023, [overrides, overrides]),
        )


@pytest.mark.parametrize("record", ["\n", "short\n"])
def test_refuses_truncated_record(record, tmp_path, monkeypatch):
    path = invented_setup(2023, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Truncated"):
        reader.read_family_income(
            2023, setup_path=path, records_path=StringIO(record)
        )


def test_refuses_blank_field(tmp_path, monkeypatch):
    path = invented_setup(2023, tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Blank"):
        reader.read_family_income(
            2023,
            setup_path=path,
            records_path=invented_records(2023, [{"head_labor": None}]),
        )


def test_legacy_reconciliation_uses_public_functions():
    income = {c: [0] for c in family_income.income_variables(2013)}
    frame = pd.DataFrame({"wave": [2013], **income})
    assert reader.reconcile_family_income(frame) == (
        family_income.reconcile_family_income(frame)
    )
    wealth = {c: [0] for c in family_income.wealth_variables(2013)}
    frame = pd.DataFrame({"wave": [2013], **wealth})
    assert reader.reconcile_wealth1(frame) == family_income.reconcile_wealth1(
        frame
    )


def test_cached_verification_rechecks_bytes_and_expected_metadata(
    tmp_path, monkeypatch
):
    path = invented_setup(2023, tmp_path, monkeypatch)
    reader.verify_setup(2023, path)
    item = reader.REGISTRY[2023]["income"]["head_labor"]
    monkeypatch.setitem(item, "label", "INVENTED_WRONG_LABEL")
    with pytest.raises(reader.UnverifiedMetadataError, match="label"):
        reader.verify_setup(2023, path)
    monkeypatch.undo()
    path = invented_setup(2023, tmp_path, monkeypatch)
    reader.verify_setup(2023, path)
    path.write_text(path.read_text() + "\nINVENTED_TAMPERING\n")
    with pytest.raises(reader.UnverifiedMetadataError, match="Unpinned"):
        reader.verify_setup(2023, path)


def test_partial_reconciliation_never_fills_missing_component():
    frame = pd.DataFrame({"wave": [2023], "total_family_income": [0]})
    with pytest.raises(KeyError):
        reader.reconcile_family_income(frame)


@pytest.mark.parametrize("wave", [2013, 2023])
def test_null_value_never_reconciles_as_zero(wave):
    if wave == 2013:
        concepts = family_income.income_variables(wave)
    else:
        concepts = reader.income_variables(wave)
    frame = pd.DataFrame({"wave": [wave], **{c: [0] for c in concepts}})
    frame["head_labor"] = pd.Series([pd.NA], dtype="Int64")
    with pytest.raises(reader.UnverifiedMetadataError, match="Missing"):
        reader.reconcile_family_income(frame)


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
@INVENTED_SETTINGS
@given(value=st.integers(-99, -1))
def test_undocumented_amount_loss_always_raises(
    value, wave, tmp_path, monkeypatch
):
    path = invented_setup(wave, tmp_path, monkeypatch)
    with pytest.raises(reader.UnverifiedMetadataError, match="head_labor"):
        reader.read_family_income(
            wave,
            setup_path=path,
            records_path=invented_records(wave, [{"head_labor": value}]),
            concepts=["head_labor"],
        )


@pytest.mark.parametrize("wave", [1999, 2001, 2003])
@INVENTED_SETTINGS
@given(code=st.sampled_from([1, 2]))
def test_undocumented_reporting_period_always_raises(
    code, wave, tmp_path, monkeypatch
):
    path = invented_setup(wave, tmp_path, monkeypatch)
    with pytest.raises(
        reader.UnverifiedMetadataError, match="head_ssi_period"
    ):
        reader.read_family_income(
            wave,
            setup_path=path,
            records_path=invented_records(wave, [{"head_ssi_period": code}]),
            concepts=["head_ssi_period"],
        )


@pytest.mark.parametrize("wave", reader.WEALTH_WAVES)
def test_wealth_amount_domain_endpoints_and_reserved_codes(
    wave, tmp_path, monkeypatch
):
    path = invented_setup(wave, tmp_path, monkeypatch)
    for concept, item in reader.wave_registry(wave)["wealth"].items():
        if item.get("allowed_codes") is not None:
            continue
        for endpoint in (item["valid_min"], item["valid_max"]):
            frame = reader.read_family_wealth(
                wave,
                setup_path=path,
                records_path=invented_records(wave, [{concept: endpoint}]),
                concepts=[concept],
            )
            assert frame.loc[0, concept] == endpoint
        reserved = item["valid_max"] + 1
        with pytest.raises(reader.UnverifiedMetadataError, match=concept):
            reader.read_family_wealth(
                wave,
                setup_path=path,
                records_path=invented_records(wave, [{concept: reserved}]),
                concepts=[concept],
            )


@pytest.mark.parametrize("wave", [1999, 2001])
def test_raw_cents_and_reporting_period_are_preserved(
    wave, tmp_path, monkeypatch
):
    path = invented_setup(wave, tmp_path, monkeypatch)
    frame = reader.read_family_income(
        wave,
        setup_path=path,
        records_path=invented_records(
            wave, [{"head_ssi_reported": 1234.56, "head_ssi_period": 5}]
        ),
        concepts=["head_ssi_reported", "head_ssi_period"],
    )
    assert frame.loc[0, "head_ssi_reported"] == 1234.56
    assert str(frame["head_ssi_reported"].dtype) == "Float64"
    assert frame.loc[0, "head_ssi_period"] == 5
    with pytest.raises(reader.UnverifiedMetadataError):
        reader.read_family_income(
            wave,
            setup_path=path,
            records_path=StringIO(""),
            concepts=["head_ssi"],
        )
