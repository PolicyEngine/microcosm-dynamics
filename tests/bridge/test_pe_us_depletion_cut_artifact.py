"""The committed depletion-cut results satisfy the analysis's identities.

Reads what ``scripts/pe_us_depletion_cut_sample_households.py`` wrote to
``docs/analysis/pe_us_depletion_cut_20261001/`` (ILLUSTRATIVE HOUSEHOLDS,
NOT SURVEY DATA; 2026 law and prices) and the committed Trustees Report
Highlights page, without starting policyengine-us, and checks:

* every artifact carries the label and the 2026-law note (the JSON, the
  Markdown, and each chart's PNG and SVG metadata);
* the citation: the page's URL, retrieval time and SHA-256 match its fetch
  record and the committed bytes, the recorded quotes are the page's own
  sentences, and the payable shares the run used are the ones parsed from
  those quotes (and Table II.A1);
* the identities, in every comparison with and without health coverage:
  the components sum exactly to the net change; the levels of government
  partition the components; the offset share is 1 - net change / Social
  Security change and the levels' shares sum to it; the Social Security
  change is minus the cut; each cut is the cut share times the benefit
  within the stated rounding; a deeper cut never leaves more Social
  Security;
* the low earner's baseline benefit equals #496's committed current-law
  benefit, and the couple's worker benefit equals the medium earner's;
* the pinned release, a fresh run from clean code, a clean float32 guard,
  and no local path;
* the generator's own code is unchanged since the commit the outputs
  record: the generator script, the scripts it imports, and the
  ``populace_dynamics`` modules either of them imports directly. Code the
  generator never names can change without touching these outputs. Not
  pinned: modules those modules import in turn; package ``__init__``
  files Python runs on the way to a dotted import (``ss/__init__.py`` for
  ``populace_dynamics.ss.params``), which today only re-export names; and
  data files that imported code reads (for example
  ``data/external/ssa_cola_history.json``, read by
  ``estimates/parameters.py``). The previous check, over all of ``src/``
  and ``scripts/``, did not pin data files either.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "docs" / "analysis" / "pe_us_depletion_cut_20261001"
SOURCES = ANALYSIS / "sources"
BRIDGE_496 = ROOT / "docs" / "analysis" / "pe_us_bridge_20260930"
STEM = "pe_us_depletion_cut_sample_households"
sys.path.insert(0, str(ROOT / "scripts"))

import pe_us_depletion_cut_sample_households as script  # noqa: E402

from populace_dynamics.bridge import depletion_cut as dc  # noqa: E402

VARIANTS = ("decomposition", "with_health_benefits_in_net_income")
GENERATOR = ROOT / "scripts" / f"{STEM}.py"


def _direct_first_party_imports(path: Path, root: Path) -> set[Path]:
    """Files under ``root`` that the module at ``path`` imports by name.

    A ``populace_dynamics`` import resolves to its module file, or to the
    package's ``__init__.py``; ``from package import submodule`` also
    resolves the submodule. A bare ``import name`` resolves to
    ``scripts/name.py`` when that file exists, since the scripts put their
    own directory on ``sys.path``.
    """

    src = root / "src"
    scripts = root / "scripts"

    def module_file(dotted: str) -> Path | None:
        base = src.joinpath(*dotted.split("."))
        if base.with_suffix(".py").is_file():
            return base.with_suffix(".py")
        if (base / "__init__.py").is_file():
            return base / "__init__.py"
        return None

    found: set[Path] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            targets = [(alias.name, []) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            targets = [(node.module or "", [a.name for a in node.names])]
        else:
            continue
        for dotted, names in targets:
            top = dotted.split(".")[0]
            if top == "populace_dynamics":
                for candidate in [dotted, *(f"{dotted}.{n}" for n in names)]:
                    resolved = module_file(candidate)
                    if resolved is not None:
                        found.add(resolved)
            elif top and (scripts / f"{top}.py").is_file():
                found.add(scripts / f"{top}.py")
    return found


def generator_sources(root: Path = ROOT) -> list[str]:
    """The code the committed outputs are pinned to, as repo-relative paths.

    The generator script, every script it imports, and the
    ``populace_dynamics`` modules any of those scripts import directly.
    """

    generator = root / "scripts" / f"{STEM}.py"
    script_files = {generator}
    pending = [generator]
    while pending:
        for found in _direct_first_party_imports(pending.pop(), root):
            if found.parent == root / "scripts" and found not in script_files:
                script_files.add(found)
                pending.append(found)
    sources = set(script_files)
    for script_file in script_files:
        sources |= _direct_first_party_imports(script_file, root)
    return sorted(str(path.relative_to(root)) for path in sources)


def changed_since(commit: str, paths: list[str], root: Path) -> bool:
    """Whether any of ``paths`` differs between ``commit`` and ``HEAD``."""

    result = subprocess.run(
        ["git", "diff", "--quiet", commit, "HEAD", "--", *paths],
        cwd=root,
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.returncode == 1


def _offsets(row, variant):
    """Each variant's offsets: the default's sit beside its decomposition."""

    if variant == "decomposition":
        return row["offsets"]
    return row[variant]["offsets"]


@pytest.fixture(scope="module")
def document():
    return json.loads((ANALYSIS / f"{STEM}.json").read_text())


@pytest.fixture(scope="module")
def report():
    return (ANALYSIS / f"{STEM}.md").read_text()


@pytest.fixture(scope="module")
def page_text():
    return dc.highlights_text(
        (SOURCES / script.HIGHLIGHTS_FILE).read_text(encoding="utf-8")
    )


def _cents(value):
    cents = round(value * 100)
    assert math.isclose(cents, value * 100, abs_tol=1e-6), value
    return cents


def _strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _charts():
    stems = [f"household_{key}_waterfall" for key in "abcde"]
    return [*stems, "offset_share_summary"]


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------
def test__artifact__then_every_file_is_labelled(document, report):
    label = "ILLUSTRATIVE HOUSEHOLDS, NOT SURVEY DATA"
    assert document["label"] == label
    assert document["law_year_note"] == script.LAW_YEAR_NOTE
    assert label in report and script.LAW_YEAR_NOTE in report
    assert script.LAW_YEAR_NOTE in document["caveats"]
    for stem in _charts():
        for suffix in (".png", ".svg"):
            data = (ANALYSIS / f"{stem}{suffix}").read_bytes()
            assert label.encode() in data, f"{stem}{suffix}"
            assert b"would not happen in 2026" in data, f"{stem}{suffix}"
            assert script.TITLE_PREFIX.encode() in data, f"{stem}{suffix}"


def test__artifact__then_the_2026_law_note_is_plain(document):
    note = document["law_year_note"]
    assert "2026 tax and benefit law" in note
    assert "would not happen in 2026" in note
    oasi = document["trustees_report"]["quotes"]["OASI"]
    assert f"deplete in {oasi['depletion_year']}" in note
    assert "not a projection" in note


# ---------------------------------------------------------------------------
# The Trustees Report
# ---------------------------------------------------------------------------
def test__artifact__then_the_page_matches_its_fetch_record(document):
    page = document["trustees_report"]["highlights"]
    records = {
        r["file"]: r
        for r in json.loads((SOURCES / script.FETCH_RECORD_FILE).read_text())
    }
    record = records[script.HIGHLIGHTS_FILE]
    data = (SOURCES / script.HIGHLIGHTS_FILE).read_bytes()
    assert (
        page["url"]
        == record["url"]
        == ("https://www.ssa.gov/oact/TR/2026/II_A_highlights.html")
    )
    assert page["retrieved_utc"] == record["retrieved_utc"]
    assert page["retrieved_utc"].endswith("+00:00")
    assert page["sha256"] == record["sha256"]
    assert page["sha256"] == hashlib.sha256(data).hexdigest()
    assert page["bytes"] == record["bytes"] == len(data)
    full = document["trustees_report"]["full_report"]
    assert full["url"] == records[script.FULL_REPORT_FILE]["url"]
    assert full["sha256"] == records[script.FULL_REPORT_FILE]["sha256"]
    assert full["committed"] is False
    assert not (SOURCES / script.FULL_REPORT_FILE).exists()
    assert set(full["quotes_found_on_text_page"]) == {"OASI", "OASDI"}
    assert set(full["other_phrases_found"]) == set(script.FULL_REPORT_QUOTES)
    assert full["quotes_found_on_printed_page"] == {"OASI": 5, "OASDI": 5}
    shortfall = script.FULL_REPORT_QUOTES[0]
    assert shortfall in dc.ROUNDING_RULE
    assert full["other_phrases_found"][shortfall]["printed_page"] == 46
    assert "not well-defined" not in json.dumps(document)
    assert full["text_extraction_sha256"] == script.FULL_REPORT_TEXT_SHA256


def test__artifact__then_the_quotes_are_the_pages_own(document, page_text):
    trustees = document["trustees_report"]
    found = dc.depletion_quotes(page_text)
    for fund in ("OASI", "OASDI"):
        quote = trustees["quotes"][fund]
        assert quote["text"] == found[fund]
        parsed = dc.parse_depletion_sentence(quote["text"])
        assert parsed.as_dict() == {
            k: v for k, v in quote.items() if k != "text"
        }
        assert trustees["key_results_table"][fund] == {
            "year": parsed.year,
            "percent": parsed.percent,
        }
    assert trustees["key_results_table"] == dc.key_results_table(page_text)
    for phrase in trustees["context_quotes"]:
        assert phrase in page_text


def test__artifact__then_the_shares_used_are_the_quoted_ones(
    document, page_text
):
    found = dc.depletion_quotes(page_text)
    for scenario, fund in script.REFORMS.items():
        parsed = dc.parse_depletion_sentence(found[fund])
        reform = document["reforms"][scenario]
        assert reform["fund"] == fund
        assert Decimal(reform["payable_share"]) == parsed.payable_share
        assert Decimal(reform["cut_share"]) == parsed.cut_share
        for row in document["results"]:
            if row["reform"] != scenario:
                continue
            for cut in row["cuts"].values():
                assert Decimal(cut["payable_share"]) == parsed.payable_share
    assert document["reforms"]["oasi"]["primary"] is True
    assert document["reforms"]["oasdi"]["primary"] is False
    assert document["reforms"]["oasi"]["payable_share"] == "0.78"
    assert document["reforms"]["oasdi"]["payable_share"] == "0.83"


def test__artifact__then_the_statutes_were_checked(document):
    statutes = document["provenance"]["statutes"]
    assert [s["citation"] for s in statutes] == [
        "42 USC 1381",
        "42 USC 1382e(a), (d)(1)",
        "42 USC 415(g)",
        "7 USC 2013(a)",
    ]
    records = {
        r["url"]: r
        for r in json.loads(
            (SOURCES / script.LAW_FETCH_RECORD_FILE).read_text()
        )
    }
    for statute in statutes:
        assert statute["phrases_found"] is True
        assert statute["sha256"] == records[statute["url"]]["sha256"]
        assert statute["committed"] is False


# ---------------------------------------------------------------------------
# The identities
# ---------------------------------------------------------------------------
def _levels_from(components):
    out = {level: 0 for level in dc.LEVELS}
    for c in components:
        level = dc.level_for(c["variable"], c["category"])
        out[level] += _cents(c["change"])
    return out


@pytest.mark.parametrize("variant", VARIANTS)
def test__artifact__then_components_sum_exactly_to_the_net_change(
    document, variant
):
    for row in document["results"]:
        d = row[variant]
        net = _cents(d["net_change"])
        assert sum(_cents(c["change"]) for c in d["components"]) == net
        assert (
            sum(_cents(v["change"]) for v in d["categories"].values()) == net
        )
        assert (
            _cents(d["reform_net_income"]) - _cents(d["baseline_net_income"])
            == net
        )


@pytest.mark.parametrize("variant", VARIANTS)
def test__artifact__then_the_levels_partition_the_components(
    document, variant
):
    for row in document["results"]:
        d = row[variant]
        offsets = _offsets(row, variant)
        recomputed = _levels_from(d["components"])
        recorded = {
            level: _cents(entry["change"])
            for level, entry in offsets["levels"].items()
        }
        assert recorded == recomputed
        assert sum(recorded.values()) == _cents(d["net_change"])
        assert recorded["market_income"] == recorded["unattributed"] == 0
        for key in ("baseline", "reform"):
            assert sum(
                _cents(entry[key]) for entry in offsets["levels"].values()
            ) == sum(_cents(c[key]) for c in d["components"])


@pytest.mark.parametrize("variant", VARIANTS)
def test__artifact__then_the_offset_share_is_one_less_net_over_cut(
    document, variant
):
    for row in document["results"]:
        offsets = _offsets(row, variant)
        ss = _cents(offsets["social_security_change"])
        net = _cents(offsets["net_change"])
        assert ss < 0
        share = Fraction(
            offsets["offset_share"]["numerator"],
            offsets["offset_share"]["denominator"],
        )
        assert share == 1 - Fraction(net, ss)
        assert share == dc.offset_share(net, ss)
        by_level = {
            level: Fraction(v["numerator"], v["denominator"])
            for level, v in offsets["offset_shares_by_level"].items()
        }
        assert sum(by_level.values()) == share
        assert sum(by_level[g] for g in dc.OFFSET_GROUPS) == share
        levels = offsets["levels"]
        for level, value in by_level.items():
            assert value == Fraction(-_cents(levels[level]["change"]), ss)


def test__artifact__then_social_security_falls_by_the_cut(document):
    for row in document["results"]:
        cut = sum(c["annual_cut"] for c in row["cuts"].values())
        for variant in VARIANTS:
            change = _cents(
                row[variant]["categories"]["social_security"]["change"]
            )
            assert change == -100 * cut
        assert (
            row["baseline_social_security_annual"]
            - (row["reform_social_security_annual"])
            == cut
        )


def test__artifact__then_each_cut_is_the_share_within_the_rounding(document):
    for row in document["results"]:
        for cut in row["cuts"].values():
            share = Decimal(cut["payable_share"])
            scheduled = cut["monthly_scheduled"]
            exact = (1 - share) * scheduled
            assert 0 <= cut["monthly_cut"] - exact < 1
            assert cut["monthly_payable"] == int(share * scheduled // 1)
            assert cut["annual_cut"] == 12 * cut["monthly_cut"]
            assert cut["annual_scheduled"] == 12 * scheduled
            assert cut["annual_payable"] == 12 * cut["monthly_payable"]


def test__artifact__then_a_deeper_cut_never_leaves_more(document):
    rows = {
        (r["household"], r["state"], r["reform"]): r
        for r in document["results"]
    }
    assert len(rows) == 5 * 3 * 2
    for (key, state, reform), row in rows.items():
        if reform != "oasi":
            continue
        other = rows[(key, state, "oasdi")]
        assert row["reform_social_security_annual"] <= (
            other["reform_social_security_annual"]
        )
        for person, cut in row["cuts"].items():
            assert cut["monthly_payable"] <= (
                other["cuts"][person]["monthly_payable"]
            )


def test__artifact__then_only_payer_groups_change(document):
    for row in document["results"]:
        for variant in VARIANTS:
            for c in row[variant]["components"]:
                if c["change"]:
                    assert dc.is_reviewed(c["variable"]), (
                        row["household"],
                        row["state"],
                        c["variable"],
                    )


# ---------------------------------------------------------------------------
# Benefits
# ---------------------------------------------------------------------------
def test__artifact__then_the_low_earner_is_496s_benefit(document):
    """The cross-check: the baseline is #496's committed current law."""

    committed = json.loads(
        (
            BRIDGE_496 / "pe_us_minimum_benefit_sample_households.json"
        ).read_text()
    )
    current = committed["worker"]["current_law"]
    low = document["benefits"]["low_earner"]
    assert low["current_law"] == current
    assert low["monthly_benefit"] == current["monthly_benefit"] == 743
    assert low["pia_record"] == committed["worker"]["pia_record"]
    for row in document["results"]:
        if row["household"] in "ABC":
            assert row["cuts"]["worker"]["monthly_scheduled"] == 743
            assert row["baseline_social_security_annual"] == (
                committed["results"][0]["baseline_social_security_annual"]
            )


def test__artifact__then_the_couple_is_the_medium_earner_and_spouse(
    document,
):
    medium = document["benefits"]["medium_earner"]
    couple = document["benefits"]["couple"]
    assert medium["claim_factor"] == 1.0
    assert medium["months_from_full_retirement_age"] == 0
    assert medium["years_of_coverage"]["years"] == 35
    assert couple["worker_monthly"] == medium["monthly_benefit"]
    result = couple["result"]
    assert result["family_maximum_binding"] is False
    pia = Fraction(result["pia"])
    assert pia == Fraction(repr(medium["current_law"]["pia_payment_year"]))
    original = Fraction(result["spouse_original_benefit"])
    assert original == Fraction(math.floor(pia / 2 * 10), 10)
    assert couple["spouse_monthly"] == math.floor(original)
    assert couple["spouse_months_before_full_retirement_age"] == 0
    for row in document["results"]:
        if row["household"] == "D":
            assert set(row["cuts"]) == {"worker"}
        if row["household"] == "E":
            assert row["cuts"]["spouse"]["monthly_scheduled"] == (
                couple["spouse_monthly"]
            )
        if row["household"] in "DE":
            assert row["cuts"]["worker"]["monthly_scheduled"] == (
                medium["monthly_benefit"]
            )


def test__artifact__then_the_medium_earner_benefit_is_taxable(document):
    """Household D: part of the benefit is taxable before and after."""

    for row in document["results"]:
        if row["household"] != "D":
            continue
        memo = row["memo"]
        assert memo["baseline"]["taxable_social_security"] > 0
        assert memo["reform"]["taxable_social_security"] > 0
        assert memo["reform"]["taxable_social_security"] < (
            row["reform_social_security_annual"]
        )


# ---------------------------------------------------------------------------
# Provenance and checks
# ---------------------------------------------------------------------------
def test__artifact__then_the_run_is_fresh_pinned_and_clean(document):
    provenance = document["provenance"]
    pe = provenance["policyengine_us"]
    assert pe["release"] == script.minimum.PE_US_RELEASE
    assert pe["installed"]["version"] == "2.18.0"
    assert pe["source_check"]["kind"] == "index"
    assert pe["source_check"]["published"] is True
    record = pe["record_check"]
    assert record["mismatched"] == record["missing"] == record["extra"] == 0
    assert provenance["microcosm_dynamics"]["code_dirty"] is False
    runs = provenance["pe_us_runs"]
    assert runs["reused_raw_outputs"] is False
    assert runs["cases"] == 5 * 3 * 3 * 2
    assert len(runs["run_job_sha256"]) == len(runs["trace_job_sha256"]) == 64


def test__artifact__then_the_float32_guard_is_clean(document):
    guard = document["float32_guard"]
    assert guard["uncaused_changes"] == 0
    assert guard["comparisons"] == 5 * 3 * 2 * 2
    for row in document["results"]:
        for variant in ("default", "with_health"):
            assert row["float32_guard"][variant]["uncaused_changes"] == []


def test__artifact__then_no_local_path_is_written(document, report):
    for text in [*_strings(document), report]:
        assert "/Users/" not in text
    for text in _strings(document):
        assert not text.startswith(("/", "~")), text


def test__artifact__then_health_differences_are_each_explained(document):
    explained = set(document["health_explanations"])
    differing = {
        f"{r['household']}-{r['state']}-{r['reform']}"
        for r in document["results"]
        if r["with_health_benefits_in_net_income"]["net_change"]
        != r["decomposition"]["net_change"]
    }
    assert explained == differing


def _share(value):
    return Fraction(value["numerator"], value["denominator"])


def test__artifact__then_the_summary_table_matches_the_json(document, report):
    """All ten columns of each summary row, from the JSON."""

    artifacts = {
        key
        for key, entry in document["health_explanations"].items()
        if entry["route"] == "encoding_artifact"
    }
    for row in document["results"]:
        offsets = row["offsets"]
        health = row["with_health_benefits_in_net_income"]["offsets"]
        shares = offsets["offset_shares_by_level"]
        mark = (
            "‡"
            if f"{row['household']}-{row['state']}-{row['reform']}"
            in artifacts
            else ""
        )
        money = script._money
        line = (
            f"| {row['household']} | {row['state']} | "
            f"{money(_cents(offsets['social_security_change']), signed=True)}"
            f" | {money(_cents(offsets['net_change']), signed=True)} | "
            f"{script.percent_text(_share(offsets['offset_share']))} | "
            f"{script.percent_text(_share(shares['federal']))} | "
            f"{script.percent_text(_share(shares['state']))} | "
            f"{money(_cents(health['net_change']), signed=True)}{mark} | "
            f"{script.percent_text(_share(health['offset_share']))}{mark} | "
            f"{script.percent_text(_share(health['offset_shares_by_level']['joint']))}"
            f"{mark} |"
        )
        assert line in report, line


def test__artifact__then_the_checks_before_writing_hold_again(document):
    """The script's own pre-write checks, rechecked on the JSON."""

    for row in document["results"]:
        for variant in VARIANTS:
            categories = {
                name: _cents(entry["change"])
                for name, entry in row[variant]["categories"].items()
            }
            levels = {
                name: _cents(entry["change"])
                for name, entry in _offsets(row, variant)["levels"].items()
            }
            for name in script.WRONG_WAY_CATEGORIES:
                assert categories[name] >= 0, (row["household"], name)
            for group, names in script.GROUP_CATEGORIES.items():
                assert levels[group] == sum(categories[n] for n in names)
            if variant == "decomposition":
                assert levels["joint"] == 0


def test__artifact__then_encoding_artifacts_are_labelled(document, report):
    """B in Montana under the 17% cut: Medicaid without SSI, labelled."""

    explanations = document["health_explanations"]
    artifacts = {
        key
        for key, entry in explanations.items()
        if entry["route"] == "encoding_artifact"
    }
    assert artifacts == {"B-MT-oasdi"}
    assert explanations["B-MT-oasi"]["route"] == "ssi_receipt"
    for key in artifacts:
        text = explanations[key]["text"]
        assert text.startswith(script.ARTIFACT_LABEL)
        assert "individual.yaml:80-81" in text
        assert f"- {key}: {text}" in report
    assert f"‡ {script.ARTIFACT_LABEL}: B-MT-oasdi." in report
    notes = document["medicaid_encoding_notes"]
    assert set(notes["notes"]) == {"MT"}
    assert notes["pages_committed"] is False
    assert {source["status"] for source in notes["sources"]} == {200}


def test__artifact__then_the_recorded_commit_is_this_code(document):
    """The outputs' commit is an ancestor of HEAD with the same generator.

    Only the generator's own code is pinned (``generator_sources``). The
    earlier form compared all of ``src/`` and ``scripts/``, which failed on
    every later change to unrelated code.
    """

    commit = document["provenance"]["microcosm_dynamics"]["commit"]
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=ROOT,
            capture_output=True,
        )
    except OSError:
        pytest.skip("git is not available")
    if ancestor.returncode not in (0, 1):
        pytest.skip(f"commit {commit} is not in this clone's history")
    assert ancestor.returncode == 0, f"{commit} is not an ancestor of HEAD"
    sources = generator_sources()
    assert not changed_since(commit, sources, ROOT), (
        f"the generator's code changed since the outputs were generated at "
        f"{commit}; regenerate them. Pinned files: {sources}"
    )


def test__generator_sources__then_they_name_the_generator_and_its_imports():
    """The pinned set holds the scripts and the modules they import."""

    sources = generator_sources()
    assert sources == sorted(set(sources))
    for expected in (
        f"scripts/{STEM}.py",
        "scripts/pe_us_minimum_benefit_sample_households.py",
        "src/populace_dynamics/bridge/depletion_cut.py",
        "src/populace_dynamics/bridge/policyengine_us.py",
    ):
        assert expected in sources
    for source in sources:
        assert (ROOT / source).is_file(), source
        assert source.startswith(("scripts/", "src/populace_dynamics/"))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.org",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def invented_repo(tmp_path):
    """An INVENTED repository exercising each way the generator names code.

    The generator imports a helper script, a module with ``from ... import``,
    a name that is not a module, and (inside a function) a dotted
    ``import populace_dynamics.deep.inner``. The helper imports a module the
    generator never names, and a second script; that script imports a
    module no other file names, so pinning it proves the recursion. Two
    files are never imported: ``unrelated.py`` and ``deep/__init__.py``.
    """

    try:
        _git(tmp_path, "init", "--quiet")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    package = tmp_path / "src" / "populace_dynamics" / "bridge"
    package.mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src" / "populace_dynamics" / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    (package / "depletion_cut.py").write_text("CUT = 1\n")
    (tmp_path / "src" / "populace_dynamics" / "unrelated.py").write_text(
        "X = 1\n"
    )
    (tmp_path / "src" / "populace_dynamics" / "extra.py").write_text("E = 1\n")
    (tmp_path / "src" / "populace_dynamics" / "extra_two.py").write_text(
        "F = 1\n"
    )
    deep = tmp_path / "src" / "populace_dynamics" / "deep"
    deep.mkdir()
    (deep / "__init__.py").write_text("")
    (deep / "inner.py").write_text("I = 1\n")
    (tmp_path / "scripts" / "helper.py").write_text(
        "import helper_two\nfrom populace_dynamics import extra\n"
    )
    (tmp_path / "scripts" / "helper_two.py").write_text(
        "from populace_dynamics import extra_two\n"
    )
    (tmp_path / "scripts" / f"{STEM}.py").write_text(
        "import helper\n"
        "from populace_dynamics.bridge import depletion_cut as dc\n"
        "from populace_dynamics.bridge import not_a_module\n"
        "\n"
        "\n"
        "def later():\n"
        "    import populace_dynamics.deep.inner\n"
    )
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "--quiet", "-m", "generated")
    return tmp_path, _git(tmp_path, "rev-parse", "HEAD")


def test__given_the_invented_repo__then_exactly_the_named_code_is_pinned(
    invented_repo,
):
    """Each import form resolves; a name that is not a module resolves to nothing."""

    root, _ = invented_repo
    assert generator_sources(root) == [
        "scripts/helper.py",
        "scripts/helper_two.py",
        f"scripts/{STEM}.py",
        "src/populace_dynamics/__init__.py",
        "src/populace_dynamics/bridge/__init__.py",
        "src/populace_dynamics/bridge/depletion_cut.py",
        "src/populace_dynamics/deep/inner.py",
        "src/populace_dynamics/extra.py",
        "src/populace_dynamics/extra_two.py",
    ]


def test__given_no_change__then_the_generator_is_unchanged(invented_repo):
    root, commit = invented_repo
    assert not changed_since(commit, generator_sources(root), root)


def test__given_unrelated_code_changes__then_the_generator_is_unchanged(
    invented_repo,
):
    """New and edited code the generator never imports does not count."""

    root, commit = invented_repo
    (root / "src" / "populace_dynamics" / "unrelated.py").write_text("X = 2\n")
    (root / "src" / "populace_dynamics" / "deep" / "__init__.py").write_text(
        "D = 1\n"
    )
    (root / "src" / "populace_dynamics" / "new_module.py").write_text(
        "Y = 1\n"
    )
    (root / "scripts" / "another_script.py").write_text("Z = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", "unrelated")
    assert not changed_since(commit, generator_sources(root), root)


@pytest.mark.parametrize(
    "relative",
    [
        f"scripts/{STEM}.py",
        "scripts/helper.py",
        "src/populace_dynamics/bridge/depletion_cut.py",
        "src/populace_dynamics/bridge/__init__.py",
        "src/populace_dynamics/extra.py",
        "scripts/helper_two.py",
        "src/populace_dynamics/extra_two.py",
        "src/populace_dynamics/deep/inner.py",
    ],
)
def test__given_a_pinned_file_changes__then_the_generator_changed(
    invented_repo, relative
):
    """Each pinned file counts.

    That covers the generator, a script it imports, a direct import and its
    package ``__init__``, a module only the helper imports, a script the
    helper imports and that script's own import (the recursion), and a
    dotted import made inside a function.
    """

    root, commit = invented_repo
    assert relative in generator_sources(root)
    with (root / relative).open("a") as handle:
        handle.write("CHANGED = True\n")
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", "pinned change")
    assert changed_since(commit, generator_sources(root), root)
