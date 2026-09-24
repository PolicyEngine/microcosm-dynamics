"""Unit tests for the label-verified family income and wealth reader.

Every fixture here is INVENTED: miniature fixed-width PSID family files
written into ``tmp_path`` with the real DATA LIST / VARIABLE LABELS layout
and the adjudicated variable names and labels, so the tests exercise the
real label verification, uniqueness checks, code decoding and refusals
without any PSID data. No value below is a PSID observation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from populace_dynamics.data import family_income as fi
from tests.data.psid_fixtures import write_product

_WIDTH = 10


def _income_values(n: int = 3) -> dict[str, list[int]]:
    """Invented income values: every concept zero, then a few set."""

    values = {concept: [0] * n for concept in fi.income_variables(2011)}
    values.update(
        interview=[101, 102, 103],
        fu_size=[1, 2, 4],
        head_age=[67, 999, 70],
        head_sex=[2, 1, 1],
        wife_age=[0, 66, 0],
        n_children=[0, 0, 2],
        head_labor=[0, 5000, 0],
        head_rent=[0, -300, 0],
        head_interest=[250, 0, 0],
        head_ss=[9000, 12000, 8000],
        wife_ss=[0, 6000, 0],
        ofum_ss=[0, 0, 4000],
        head_ssi=[1200, 0, 0],
        ofum_asset=[0, 0, 50],
        ofum_labor=[0, 0, 20000],
        census_needs_standard=[10000, 13000, 20000],
    )
    values["hw_taxable"] = [250, 4700, 0]
    values["hw_transfer"] = [1200, 0, 0]
    values["ofum_taxable"] = [0, 0, 20050]
    values["total_family_income"] = [
        sum(values[c][i] for c in fi.FAMILY_INCOME_AGGREGATES)
        for i in range(n)
    ]
    return values


def _write_family(
    root: Path,
    wave: int,
    values: dict[str, list[int]],
    *,
    wealth: dict[str, list[int]] | None = None,
    relabel: dict[str, str] | None = None,
    extra: list[tuple[str, int, str, list[int]]] = (),
) -> None:
    relabel = relabel or {}
    fields = [
        (var, _WIDTH, relabel.get(concept, label), values[concept])
        for concept, (var, label) in fi.income_variables(wave).items()
    ]
    if wealth is not None:
        fields += [
            (var, _WIDTH, label, wealth[concept])
            for concept, (var, label) in fi.wealth_variables(wave).items()
        ]
    write_product(
        root / "family" / str(wave),
        f"FAM{wave}ER.sps",
        f"FAM{wave}ER.txt",
        [*fields, *extra],
    )


def _wealth_values() -> dict[str, list[int]]:
    values = {concept: [0, 0, 0] for concept in fi.wealth_variables(2011)}
    values.update(
        checking_saving=[5000, 20000, 0],
        vehicles=[3000, 8000, 1000],
        ira_annuity=[0, 50000, 0],
        credit_card_debt=[0, 2000, 4000],
        home_equity=[0, 90000, 0],
    )
    assets = [
        sum(values[c][i] for c in fi.WEALTH1_ASSETS[2011]) for i in range(3)
    ]
    debts = [
        sum(values[c][i] for c in fi.WEALTH1_DEBTS[2011]) for i in range(3)
    ]
    values["wealth1"] = [a - d for a, d in zip(assets, debts, strict=True)]
    values["wealth2"] = [
        w + h
        for w, h in zip(values["wealth1"], values["home_equity"], strict=True)
    ]
    values["wealth1_acc"] = [0, 1, 0]
    return values


def test_tables_cover_the_waves_and_concepts():
    assert fi.INCOME_WAVES == (2005, 2007, 2009, 2011, 2013)
    assert fi.WEALTH_WAVES == (2009, 2011, 2013)
    assert fi.WEALTH_SUPPLEMENT_WAVES == (2005, 2007)
    for wave in fi.INCOME_WAVES:
        table = fi.income_variables(wave)
        for concept in (
            *fi.ASSET_INCOME_CONCEPTS,
            *fi.SOCIAL_SECURITY_CONCEPTS,
            *fi.SSI_CONCEPTS,
            *fi.FAMILY_INCOME_AGGREGATES,
            *fi.HW_EARNED_CONCEPTS,
            *fi.HW_TRANSFER_COMPONENTS[wave],
            *fi.OFUM_TRANSFER_COMPONENTS,
        ):
            assert concept in table, (wave, concept)
        labels = [label for _, label in table.values()]
        assert len(labels) == len(set(labels))
        for concept, (_, label) in table.items():
            if label.endswith(f"-{wave - 1}"):
                continue
            assert concept in {
                "interview",
                "fu_size",
                "head_age",
                "head_sex",
                "wife_age",
                "n_children",
            }, (wave, concept, label)
    for wave in fi.WEALTH_WAVES:
        table = fi.wealth_variables(wave)
        for concept in (*fi.WEALTH1_ASSETS[wave], *fi.WEALTH1_DEBTS[wave]):
            assert concept in table
        assert table["wealth1"][1].startswith("IMP WEALTH W/O EQUITY")


def test_income_reader_decodes_an_invented_wave(tmp_path):
    _write_family(tmp_path, 2011, _income_values())
    frame = fi.read_family_income(2011, data_dir=tmp_path)
    assert list(frame["wave"]) == [2011] * 3
    assert list(frame["income_year"]) == [2010] * 3
    assert list(frame["interview"]) == [101, 102, 103]
    assert list(frame["head_sex"]) == ["female", "male", "male"]
    assert frame["head_age"].isna().tolist() == [False, True, False]
    assert frame["wife_present"].tolist() == [False, True, False]
    assert frame["wife_age"].tolist()[1] == 66
    assert frame["wife_age"].isna().tolist() == [True, False, True]
    assert frame.loc[1, "head_rent"] == -300
    assert frame.loc[0, "head_ssi"] == 1200


def test_income_reader_rejects_a_relabelled_variable(tmp_path):
    _write_family(
        tmp_path,
        2011,
        _income_values(),
        relabel={"head_ssi": "HEAD SSI-2009"},
    )
    with pytest.raises(ValueError, match="does not match"):
        fi.read_family_income(2011, data_dir=tmp_path)


def test_income_reader_rejects_a_second_variable_with_the_label(tmp_path):
    _write_family(
        tmp_path,
        2011,
        _income_values(),
        extra=[("ER99999", _WIDTH, "HEAD SSI-2010", [0, 0, 0])],
    )
    with pytest.raises(ValueError, match="carried by"):
        fi.read_family_income(2011, data_dir=tmp_path)


def test_income_reader_refuses_undocumented_negatives(tmp_path):
    values = _income_values()
    values["head_ss"] = [-1, 0, 0]
    _write_family(tmp_path, 2011, values)
    with pytest.raises(ValueError, match="negative head_ss"):
        fi.read_family_income(2011, data_dir=tmp_path)


def test_income_reader_accepts_documented_losses(tmp_path):
    values = _income_values()
    values["head_farm"] = [0, -2500, 0]
    values["head_business_asset"] = [-10, 0, 0]
    _write_family(tmp_path, 2011, values)
    frame = fi.read_family_income(2011, data_dir=tmp_path)
    assert frame.loc[1, "head_farm"] == -2500
    assert "head_farm" in fi.MAY_BE_NEGATIVE


@pytest.mark.parametrize(
    "concept, bad",
    [
        ("head_sex", [3, 1, 1]),
        ("head_age", [0, 60, 60]),
        ("wife_age", [998, 0, 0]),
        ("fu_size", [0, 2, 4]),
        ("n_children", [1, 0, 2]),
        ("census_needs_standard", [0, 13000, 20000]),
    ],
)
def test_income_reader_rejects_undocumented_codes(tmp_path, concept, bad):
    values = _income_values()
    values[concept] = bad
    _write_family(tmp_path, 2011, values)
    with pytest.raises(ValueError):
        fi.read_family_income(2011, data_dir=tmp_path)


def test_income_reader_rejects_undocumented_accuracy_codes(tmp_path):
    values = _income_values()
    values["head_ssi_acc"] = [0, 12, 0]
    _write_family(tmp_path, 2011, values)
    with pytest.raises(ValueError, match="accuracy codes"):
        fi.read_family_income(2011, data_dir=tmp_path)


def test_income_reader_rejects_duplicate_interviews(tmp_path):
    values = _income_values()
    values["interview"] = [101, 101, 103]
    _write_family(tmp_path, 2011, values)
    with pytest.raises(ValueError, match="duplicate interview"):
        fi.read_family_income(2011, data_dir=tmp_path)


def test_readers_refuse_unresolved_waves():
    with pytest.raises(ValueError, match="outside"):
        fi.income_variables(2003)
    with pytest.raises(ValueError, match="outside"):
        fi.wealth_variables(2015)
    with pytest.raises(fi.WealthSupplementNotAdjudicatedError):
        fi.wealth_variables(2005)


def test_wealth_reader_reads_components(tmp_path):
    _write_family(tmp_path, 2011, _income_values(), wealth=_wealth_values())
    frame = fi.read_family_wealth(2011, data_dir=tmp_path)
    assert list(frame["interview"]) == [101, 102, 103]
    assert list(frame["wealth1"]) == [8000, 76000, -3000]
    assert list(frame["wealth1_acc"]) == [0, 1, 0]
    counts = fi.reconcile_wealth1(frame)["2011"]
    assert counts["wealth1"]["n_exact"] == 3
    assert counts["wealth2"]["n_exact"] == 3


def test_wealth_reader_rejects_undocumented_accuracy(tmp_path):
    wealth = _wealth_values()
    wealth["wealth1_acc"] = [0, 2, 0]
    _write_family(tmp_path, 2011, _income_values(), wealth=wealth)
    with pytest.raises(ValueError, match="accuracy"):
        fi.read_family_wealth(2011, data_dir=tmp_path)


def test_wealth_reader_rejects_negative_debt(tmp_path):
    wealth = _wealth_values()
    wealth["credit_card_debt"] = [0, -5, 0]
    _write_family(tmp_path, 2011, _income_values(), wealth=wealth)
    with pytest.raises(ValueError, match="negative credit_card_debt"):
        fi.read_family_wealth(2011, data_dir=tmp_path)


def _write_2005(root: Path, *, wealth_label: bool = False) -> None:
    values = {concept: [0, 0] for concept in fi.income_variables(2005)}
    values.update(
        interview=[1, 2], fu_size=[1, 1], head_age=[67, 67], head_sex=[1, 2]
    )
    values["census_needs_standard"] = [9000, 9000]
    extra = (
        [("ER99998", 9, "IMP WEALTH W/O EQUITY (WEALTH1) 05", [0, 0])]
        if wealth_label
        else []
    )
    fields = [
        (var, _WIDTH, label, values[concept])
        for concept, (var, label) in fi.income_variables(2005).items()
    ]
    write_product(
        root / "family" / "2005",
        "FAM2005ER.sps",
        "FAM2005ER.txt",
        [*fields, *extra],
    )


def test_supplement_wave_refusal_names_the_missing_files(tmp_path):
    _write_2005(tmp_path)
    with pytest.raises(fi.WealthSupplementNotStagedError) as error:
        fi.read_family_wealth(2005, data_dir=tmp_path)
    message = str(error.value)
    assert "2005 wealth supplement not staged" in message
    assert str(tmp_path / "wealth" / "2005") in message
    assert ".sps" in message and ".txt" in message
    assert "Max" in message
    status = fi.wealth_supplement_status(2005, data_dir=tmp_path)
    assert status["staged"] is False


def test_staged_but_unadjudicated_supplement_is_refused(tmp_path):
    _write_2005(tmp_path)
    staged = tmp_path / "wealth" / "2005"
    staged.mkdir(parents=True)
    (staged / "WLTH2005.sps").write_text("invented\n")
    (staged / "WLTH2005.txt").write_text("invented\n")
    assert fi.wealth_supplement_status(2005, data_dir=tmp_path)["staged"]
    with pytest.raises(fi.WealthSupplementNotAdjudicatedError):
        fi.read_family_wealth(2005, data_dir=tmp_path)


def test_supplement_premise_is_checked(tmp_path):
    _write_2005(tmp_path, wealth_label=True)
    with pytest.raises(ValueError, match="premise"):
        fi.read_family_wealth(2005, data_dir=tmp_path)


def test_income_reconciliation_counts_misses(tmp_path):
    values = _income_values()
    values["total_family_income"] = [
        values["total_family_income"][0] + 50,
        *values["total_family_income"][1:],
    ]
    _write_family(tmp_path, 2011, values)
    frame = fi.read_family_income(2011, data_dir=tmp_path)
    counts = fi.reconcile_family_income(frame)["2011"]
    assert counts["total_family_income"] == {
        "n_families": 3,
        "n_exact": 2,
        "n_within_tolerance": 2,
        "n_beyond_tolerance": 1,
    }
    # 102: labor 5000 + rent -300 = 4700; 101: interest 250.
    assert counts["hw_taxable"]["n_exact"] == 3
    assert counts["ofum_taxable"]["n_exact"] == 3
    assert counts["hw_transfer"]["n_exact"] == 3
    assert counts["ofum_transfer"]["n_exact"] == 3


def test_reconciliation_handles_several_waves():
    frame = pd.DataFrame(
        {
            "wave": [2009, 2011],
            **{
                concept: [0, 0]
                for concept in {
                    *fi.FAMILY_INCOME_AGGREGATES,
                    *fi.HW_EARNED_CONCEPTS,
                    *fi.ASSET_INCOME_CONCEPTS,
                    *fi.HW_TRANSFER_COMPONENTS[2011],
                    *fi.OFUM_TRANSFER_COMPONENTS,
                    "ofum_labor",
                    "total_family_income",
                }
            },
        }
    )
    counts = fi.reconcile_family_income(frame)
    assert set(counts) == {"2009", "2011"}
