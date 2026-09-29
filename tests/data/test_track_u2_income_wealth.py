"""Documentary U2 coverage; these tests never open PSID raw records."""

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WAVES = (2013, 2015, 2017, 2019, 2021, 2023)


def registry(name):
    path = ROOT / "data/external/track_u2" / f"{name}.json"
    return json.loads(path.read_text())


def u1_routes(name):
    path = ROOT / "src/populace_dynamics/data/family_income.py"
    tree = ast.parse(path.read_text())
    wanted = (
        ("_INCOME_VARS", "_ACCURACY_VARS")
        if name == "income"
        else ("_WEALTH_VARS",)
    )
    routes = set()
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in wanted
        ):
            for wave_routes in ast.literal_eval(node.value).values():
                routes.update(wave_routes)
    assert routes
    return routes


@pytest.mark.parametrize("name", ["income", "wealth"])
@pytest.mark.parametrize("wave", WAVES)
def test_every_u1_boundary_route_has_documentary_u2_mapping(name, wave):
    data = registry(name)
    assert data["target_id"] == "U2"
    entries = [entry for entry in data["entries"] if entry["wave"] == wave]
    assert u1_routes(name) <= {entry["route"] for entry in entries}
    for entry in entries:
        if entry.get("kind") == "historical_route_crosswalk":
            assert all(var.startswith("ER") for var in entry["variables"])
            assert len(entry["variables"]) > 1
        else:
            assert entry["variable"].startswith("ER")
            assert entry["width"] == (
                entry["position_end"] - entry["position_start"] + 1
            )
        assert entry["codebook_text"]
        assert entry["documented_domain"]
        assert any("page" in item for item in entry["citations"])
        assert any("line" in item for item in entry["citations"])
        if entry["status"] == "TO VERIFY":
            assert entry["question"]
    assert all(
        source["file"].endswith((".sps", ".pdf")) for source in data["sources"]
    )


@pytest.mark.parametrize("wave", WAVES)
def test_documented_composite_identities_and_split_accounts(wave):
    income = {
        entry["route"]: entry
        for entry in registry("income")["entries"]
        if entry["wave"] == wave
    }
    wealth = {
        entry["route"]: entry
        for entry in registry("wealth")["entries"]
        if entry["wave"] == wave
    }
    aggregate = income["total_family_income"]
    terms = aggregate["identity"]["terms"]
    assert len(terms) == len(set(terms)) == 7
    assert all(term in aggregate["codebook_text"] for term in terms)
    assert aggregate["reference_year"] == wave - 1
    composite = wealth["wealth1"]
    identity = composite["identity"]
    assets, debts = identity["assets"], identity["debts"]
    assert len(assets) == len(set(assets)) == (7 if wave < 2019 else 8)
    assert len(debts) == len(set(debts)) == 8
    assert not set(assets) & set(debts)
    assert identity["excluded_home_equity"] not in assets + debts
    assert all(var in composite["codebook_text"] for var in assets + debts)
    assert wealth["farm_business_debt"]["variable"] in debts
    assert wealth["other_real_estate_debt"]["variable"] in debts
    assert ("cd_bonds_treasury" in wealth) == (wave >= 2019)
    assert composite["reference_year"] == wave


def test_documentary_accuracy_conflicts_are_preserved():
    entries = registry("wealth")["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    resolved = 0
    for entry in entries:
        if entry["route"] == "wealth2_acc" or (
            entry["route"] == "checking_saving_acc" and entry["wave"] < 2019
        ):
            # Independent adjudication D (amendment 4): the corrected target
            # is recorded and the contradictory codebook wording is kept.
            assert entry["status"] == "RESOLVED"
            assert "question" not in entry
            assert entry["adjudication"]["disposition"] == "D"
            conflict = entry["source_wording_conflict"]
            wrong = conflict["codebook_states_accuracy_of"]
            target = conflict["resolved_accuracy_for_variable"]
            assert target == entry["accuracy_for_variable"] != wrong
            assert f"Accuracy of {wrong}" in entry["codebook_text"]
            amount = by_id[entry["id"].removesuffix("_acc")]
            assert amount["variable"] == target
            assert "never changes amounts" in entry["use_restriction"]
            resolved += 1
    assert resolved == 9


def test_later_income_slot_maps_cannot_waive_role_blockers():
    roles = {entry["id"]: entry for entry in registry("roles")["entries"]}
    for entry in registry("income")["entries"]:
        if entry["wave"] > 2013 and entry["route"].startswith(
            ("head_", "wife_", "hw_", "ofum_")
        ):
            if entry["wave"] == 2017:
                # Both 2017 blockers (codes 90 and 92) were resolved from
                # documents by the independent adjudication (D).
                assert "blocking_dependencies" not in entry
                for code in (90, 92):
                    role = roles[f"2017.relationship.{code}"]
                    assert role["status"] == "RESOLVED"
                    assert role["action"] == "documented_rule"
                continue
            assert entry["blocking_dependencies"]
            for dependency in entry["blocking_dependencies"]:
                role = roles[dependency.removeprefix("roles:")]
                assert role["action"].startswith("refuse")
