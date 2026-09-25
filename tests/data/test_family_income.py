"""Unit tests for the label-verified family income and wealth reader.

Every fixture here is INVENTED: miniature fixed-width PSID family files
written into ``tmp_path`` with the real DATA LIST / VARIABLE LABELS layout
and the adjudicated variable names and labels, so the tests exercise the
real label verification, uniqueness checks, code decoding and refusals
without any PSID data. No value below is a PSID observation.
"""

from __future__ import annotations

import hashlib
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
    with pytest.raises(ValueError, match="outside"):
        fi.wealth_variables(2003)


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


def _write_2005(
    root: Path,
    *,
    wealth_label: bool = False,
    interviews: tuple[int, ...] = (1, 2),
) -> None:
    n = len(interviews)
    values = {concept: [0] * n for concept in fi.income_variables(2005)}
    values.update(
        interview=list(interviews),
        fu_size=[1] * n,
        head_age=[67] * n,
        head_sex=[1, 2] * (n // 2) + [1] * (n % 2),
    )
    values["census_needs_standard"] = [9000] * n
    extra = (
        [("ER99998", 9, "IMP WEALTH W/O EQUITY (WEALTH1) 05", [0] * n)]
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


def _supplement_values(
    interviews: tuple[int, ...] = (1, 2, 3),
) -> dict[str, list[int]]:
    """Invented 2005 supplement values whose WEALTH1 adds up."""

    n = len(interviews)
    values = {
        concept: [0] * n for concept in fi.wealth_supplement_variables(2005)
    }
    values.update(
        release=[2] * n,
        interview=list(interviews),
        checking_saving=[5000, 20000, -40][:n],
        vehicles=[3000, 8000, 1000][:n],
        ira_annuity=[0, 50000, 0][:n],
        farm_business=[0, 0, -700][:n],
        other_debt=[0, 2000, 4000][:n],
        home_equity=[0, 90000, -500][:n],
        vehicles_acc=[0, 1, 0][:n],
        wealth1_acc=[0, 1, 0][:n],
    )
    assets = [
        sum(values[c][i] for c in fi.WEALTH1_ASSETS[2005]) for i in range(n)
    ]
    debts = [
        sum(values[c][i] for c in fi.WEALTH1_DEBTS[2005]) for i in range(n)
    ]
    values["wealth1"] = [a - d for a, d in zip(assets, debts, strict=True)]
    values["wealth2"] = [
        w + h
        for w, h in zip(values["wealth1"], values["home_equity"], strict=True)
    ]
    return values


def _write_supplement(
    root: Path,
    monkeypatch,
    values: dict[str, list[int]],
    *,
    relabel: dict[str, str] | None = None,
    pin: bool = True,
) -> None:
    """An INVENTED 2005 supplement under ``root/wealth/2005``; ``pin``
    makes its bytes the adjudicated ones for this test only."""

    relabel = relabel or {}
    directory = root / "wealth" / "2005"
    write_product(
        directory,
        "WLTH2005.sps",
        "WLTH2005.txt",
        [
            (var, _WIDTH, relabel.get(concept, label), values[concept])
            for concept, (var, label) in fi.wealth_supplement_variables(
                2005
            ).items()
        ],
    )
    if pin:
        monkeypatch.setitem(
            fi.WEALTH_SUPPLEMENT_SHA256,
            2005,
            {
                name: hashlib.sha256(
                    (directory / name).read_bytes()
                ).hexdigest()
                for name in ("WLTH2005.sps", "WLTH2005.txt")
            },
        )


def test_supplement_tables_mirror_the_2009_family_file():
    """The 2005 and 2007 supplement tables (adjudicated 2026-09-25) carry
    the 2009 family file's wealth concepts item for item, with the wave
    token on every label and each accuracy flag the variable after its
    amount."""

    for wave, token in ((2005, "05"), (2007, "07")):
        table = fi.wealth_variables(wave)
        assert list(table) == list(fi.wealth_variables(2009))
        assert fi.WEALTH1_ASSETS[wave] == fi.WEALTH1_ASSETS[2009]
        assert fi.WEALTH1_DEBTS[wave] == fi.WEALTH1_DEBTS[2009]
        full = fi.wealth_supplement_variables(wave)
        assert full["interview"] == (
            {2005: "S701", 2007: "S801"}[wave],
            f"{wave} FAMILY ID",
        )
        assert full["release"][1] == f"{wave} WEALTH FILE RELEASE NUMBER"
        assert table["wealth1"][1] == (
            f"IMP WEALTH W/O EQUITY (WEALTH1) {token}"
        )
        for concept, (var, label) in full.items():
            if concept in ("interview", "release"):
                continue
            assert label.endswith(f" {token}"), concept
            if concept.endswith("_acc"):
                amount_var, amount_label = full[concept[: -len("_acc")]]
                assert var == f"{amount_var}A"
                assert label == "ACC" + amount_label[len("IMP") :]
        accuracy = [c for c in full if c.endswith("_acc")]
        amounts = [c for c in table if c != "wealth1_acc"]
        assert sorted(accuracy) == sorted(f"{c}_acc" for c in amounts)
        assert set(fi.WEALTH_SUPPLEMENT_SHA256[wave]) == {
            f"WLTH{wave}.sps",
            f"WLTH{wave}.txt",
        }
    with pytest.raises(ValueError, match="not a supplement wave"):
        fi.wealth_supplement_variables(2009)


def test_supplement_wave_refusal_names_the_missing_files(tmp_path):
    _write_2005(tmp_path)
    with pytest.raises(fi.WealthSupplementNotStagedError) as error:
        fi.read_family_wealth(2005, data_dir=tmp_path)
    message = str(error.value)
    assert "2005 wealth supplement not staged" in message
    assert str(tmp_path / "wealth" / "2005") in message
    assert ".sps" in message and ".txt" in message
    assert "WLTH2005.sps" in message and "wlth2005.zip" in message
    status = fi.wealth_supplement_status(2005, data_dir=tmp_path)
    assert status["staged"] is False
    assert status["adjudicated"] is False


def test_staged_but_unadjudicated_supplement_is_refused(tmp_path):
    _write_2005(tmp_path)
    staged = tmp_path / "wealth" / "2005"
    staged.mkdir(parents=True)
    (staged / "WLTH2005.sps").write_text("invented\n")
    (staged / "WLTH2005.txt").write_text("invented\n")
    status = fi.wealth_supplement_status(2005, data_dir=tmp_path)
    assert status["staged"] and not status["adjudicated"]
    with pytest.raises(
        fi.WealthSupplementNotAdjudicatedError, match="adjudicated on"
    ):
        fi.read_family_wealth(2005, data_dir=tmp_path)


def test_supplement_premise_is_checked(tmp_path):
    _write_2005(tmp_path, wealth_label=True)
    with pytest.raises(ValueError, match="premise"):
        fi.read_family_wealth(2005, data_dir=tmp_path)


def test_supplement_reader_reads_an_invented_supplement(tmp_path, monkeypatch):
    _write_2005(tmp_path, interviews=(1, 2, 3))
    _write_supplement(tmp_path, monkeypatch, _supplement_values())
    assert fi.wealth_supplement_status(2005, data_dir=tmp_path)["adjudicated"]
    frame = fi.read_family_wealth(2005, data_dir=tmp_path)
    assert list(frame.columns) == [
        "wave",
        "interview",
        *fi.wealth_variables(2005),
    ]
    assert list(frame["wave"]) == [2005] * 3
    assert list(frame["interview"]) == [1, 2, 3]
    assert list(frame["wealth1"]) == [8000, 76000, -3740]
    assert list(frame["wealth1_acc"]) == [0, 1, 0]
    # documented negatives (checking/saving, farm/business, home equity)
    # are accepted
    assert frame.loc[2, "farm_business"] == -700
    counts = fi.reconcile_wealth1(frame)["2005"]
    assert counts["wealth1"]["n_exact"] == 3
    assert counts["wealth2"]["n_exact"] == 3
    assert fi.wealth_supplement_join(2005, data_dir=tmp_path) == {
        "n_supplement_records": 3,
        "n_family_file_records": 3,
        "n_matched": 3,
        "n_supplement_only": 0,
        "n_family_file_only": 0,
    }


def test_supplement_bytes_other_than_the_pinned_are_refused(
    tmp_path, monkeypatch
):
    _write_2005(tmp_path, interviews=(1, 2, 3))
    _write_supplement(tmp_path, monkeypatch, _supplement_values(), pin=False)
    with pytest.raises(fi.WealthSupplementNotAdjudicatedError):
        fi.read_family_wealth(2005, data_dir=tmp_path)
    with pytest.raises(fi.WealthSupplementNotAdjudicatedError):
        fi.wealth_supplement_join(2005, data_dir=tmp_path)


@pytest.mark.parametrize(
    "concept, label, match",
    [
        ("wealth1", "IMP WEALTH W/O EQUITY (WEALTH1) 07", "does not match"),
        ("other_debt_acc", "ACC VALUE OTH DEBT (W38) 05", "does not match"),
        ("interview", "2005 INTERVIEW NUMBER", "does not match"),
    ],
)
def test_supplement_reader_rejects_a_relabelled_variable(
    tmp_path, monkeypatch, concept, label, match
):
    _write_2005(tmp_path, interviews=(1, 2, 3))
    _write_supplement(
        tmp_path, monkeypatch, _supplement_values(), relabel={concept: label}
    )
    with pytest.raises(ValueError, match=match):
        fi.read_family_wealth(2005, data_dir=tmp_path)


@pytest.mark.parametrize(
    "concept, bad, match",
    [
        ("release", [1, 2, 2], "Release 2"),
        ("vehicles_acc", [0, 3, 0], "accuracy"),
        ("wealth1_acc", [0, 2, 0], "accuracy"),
        ("other_debt", [0, -5, 0], "negative other_debt"),
        ("ira_annuity", [0, -1, 0], "negative ira_annuity"),
        ("interview", [1, 1, 3], "duplicate"),
        ("interview", [0, 2, 3], "non-positive"),
    ],
)
def test_supplement_reader_rejects_undocumented_codes(
    tmp_path, monkeypatch, concept, bad, match
):
    _write_2005(tmp_path, interviews=(1, 2, 3))
    values = _supplement_values()
    values[concept] = bad
    _write_supplement(tmp_path, monkeypatch, values)
    with pytest.raises(ValueError, match=match):
        fi.read_family_wealth(2005, data_dir=tmp_path)


def test_supplement_family_id_must_join_the_family_file(tmp_path, monkeypatch):
    # a supplement record whose family ID is no 2005 interview number
    _write_2005(tmp_path, interviews=(1, 2, 3))
    _write_supplement(tmp_path, monkeypatch, _supplement_values((1, 2, 9)))
    with pytest.raises(ValueError, match="one to one"):
        fi.read_family_wealth(2005, data_dir=tmp_path)
    assert fi.wealth_supplement_join(2005, data_dir=tmp_path) == {
        "n_supplement_records": 3,
        "n_family_file_records": 3,
        "n_matched": 2,
        "n_supplement_only": 1,
        "n_family_file_only": 1,
    }


def test_a_complete_supplement_read_covers_every_family(tmp_path, monkeypatch):
    _write_2005(tmp_path, interviews=(1, 2, 3, 4))
    _write_supplement(tmp_path, monkeypatch, _supplement_values())
    with pytest.raises(ValueError, match="one to one"):
        fi.read_family_wealth(2005, data_dir=tmp_path)
    # a partial read checks only that its records join
    assert len(fi.read_family_wealth(2005, data_dir=tmp_path, nrows=2)) == 2


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
