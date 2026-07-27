"""Reproduction and fail-closed pins for the vintage-1 SSA level anchors."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SNAPSHOTS = (
    ROOT / "data" / "external" / "snapshots" / "ssa_level_anchors_vintage1"
)
ARTIFACT = (
    ROOT
    / "data"
    / "external"
    / "ssa_level_anchors_supplement2025_trustees2026_vintage1.json"
)
ARTIFACT_SHA256 = (
    "adc782a1a11c50969103c125a82b1539a7017241662d545d86bc6fc9227730c1"
)

EXPECTED_SERIES_IDS = (
    "retired_worker_awards",
    "retired_worker_benefits_paid_estimated_allocation",
    "oasi_benefits_paid_estimated_allocation",
    "oasi_trust_fund_benefit_payments",
    "oasdi_trust_fund_benefit_payments",
    "retired_worker_december_current_payment_stock",
    "oasi_december_current_payment_stock",
    "oasdi_december_current_payment_stock",
    "oasdi_workers_with_taxable_earnings",
    "oasdi_reported_taxable_earnings",
    "oasdi_gross_contributions",
    "oasdi_adjusted_taxable_payroll",
    "oasdi_covered_workers",
    "oasi_net_payroll_tax_contributions",
    "oasdi_net_payroll_tax_contributions",
)
EXPECTED_YEARS = tuple(range(2015, 2023))

# These are independent literals from the pre-implementation scoping survey.
# The test deliberately compares the published tokens, before normalization.
EXPECTED_AS_PUBLISHED = {
    "retired_worker_awards": (
        "2,838,988",
        "2,910,752",
        "2,974,639",
        "3,082,080",
        "3,174,673",
        "3,367,537",
        "3,186,183",
        "3,413,289",
    ),
    "retired_worker_benefits_paid_estimated_allocation": (
        "592,423",
        "616,003",
        "644,181",
        "686,099",
        "737,809",
        "783,504",
        "822,440",
        "906,826",
    ),
    "oasi_benefits_paid_estimated_allocation": (
        "742,939",
        "768,633",
        "798,722",
        "844,924",
        "902,833",
        "952,388",
        "993,167",
        "1,088,170",
    ),
    "oasi_trust_fund_benefit_payments": (
        "742,908",
        "768,603",
        "798,692",
        "844,895",
        "902,809",
        "952,362",
        "993,133",
        "1,088,140",
    ),
    "oasdi_trust_fund_benefit_payments": (
        "886,278",
        "911,384",
        "941,499",
        "988,635",
        "1,047,930",
        "1,095,924",
        "1,133,191",
        "1,231,707",
    ),
    "retired_worker_december_current_payment_stock": (
        "40,089,061",
        "41,233,126",
        "42,446,992",
        "43,721,450",
        "45,094,245",
        "46,329,595",
        "47,292,977",
        "48,587,883",
    ),
    "oasi_december_current_payment_stock": (
        "49,156,959",
        "50,297,237",
        "51,492,108",
        "52,743,734",
        "54,139,028",
        "55,232,480",
        "56,010,158",
        "57,153,724",
    ),
    "oasdi_december_current_payment_stock": (
        "59,963,425",
        "60,907,307",
        "61,903,360",
        "62,906,222",
        "64,064,496",
        "64,850,867",
        "65,228,238",
        "65,994,457",
    ),
    "oasdi_workers_with_taxable_earnings": (
        "168,186",
        "170,738",
        "172,744",
        "175,065",
        "176,993",
        "175,244",
        "176,995",
        "181,099",
    ),
    "oasdi_reported_taxable_earnings": (
        "6,470,900",
        "6,663,400",
        "7,005,500",
        "7,338,200",
        "7,695,900",
        "7,747,895",
        "8,390,884",
        "9,186,239",
    ),
    "oasdi_gross_contributions": (
        "802,392",
        "826,262",
        "868,682",
        "909,937",
        "954,292",
        "960,739",
        "1,040,470",
        "1,139,094",
    ),
    "oasdi_adjusted_taxable_payroll": (
        "6,448",
        "6,639",
        "6,983",
        "7,313",
        "7,666",
        "7,718",
        "8,346",
        "9,134",
    ),
    "oasdi_covered_workers": (
        "168,143",
        "170,631",
        "172,688",
        "175,114",
        "177,088",
        "175,207",
        "177,080",
        "181,068",
    ),
    "oasi_net_payroll_tax_contributions": (
        "679,503",
        "678,787",
        "706,505",
        "715,865",
        "805,091",
        "855,979",
        "838,235",
        "945,924",
    ),
    "oasdi_net_payroll_tax_contributions": (
        "794,892",
        "836,178",
        "873,592",
        "885,051",
        "944,468",
        "1,001,272",
        "980,602",
        "1,106,602",
    ),
}

EXPECTED_UNITS = {
    "retired_worker_awards": ("awards", "awards", 1),
    "retired_worker_benefits_paid_estimated_allocation": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "oasi_benefits_paid_estimated_allocation": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "oasi_trust_fund_benefit_payments": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "oasdi_trust_fund_benefit_payments": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "retired_worker_december_current_payment_stock": (
        "persons",
        "persons",
        1,
    ),
    "oasi_december_current_payment_stock": ("persons", "persons", 1),
    "oasdi_december_current_payment_stock": ("persons", "persons", 1),
    "oasdi_workers_with_taxable_earnings": (
        "thousands_of_persons",
        "persons",
        1_000,
    ),
    "oasdi_reported_taxable_earnings": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "oasdi_gross_contributions": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "oasdi_adjusted_taxable_payroll": (
        "billions_of_current_dollars",
        "current_dollars",
        1_000_000_000,
    ),
    "oasdi_covered_workers": (
        "thousands_of_persons",
        "persons",
        1_000,
    ),
    "oasi_net_payroll_tax_contributions": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
    "oasdi_net_payroll_tax_contributions": (
        "millions_of_current_dollars",
        "current_dollars",
        1_000_000,
    ),
}

EXPECTED_COLUMN_PATHS = {
    "retired_worker_awards": ("Retired workers",),
    "retired_worker_benefits_paid_estimated_allocation": (
        "Retired-worker and dependents benefits",
        "Retired workers",
    ),
    "oasi_benefits_paid_estimated_allocation": ("Total",),
    "oasi_trust_fund_benefit_payments": (
        "Expenditures",
        "Benefit payments e",
    ),
    "oasdi_trust_fund_benefit_payments": (
        "Expenditures",
        "Benefit payments e",
    ),
    "retired_worker_december_current_payment_stock": ("Retired workers",),
    "oasi_december_current_payment_stock": ("OASDI", "OASI Trust Fund"),
    "oasdi_december_current_payment_stock": ("OASDI", "Total"),
    "oasdi_workers_with_taxable_earnings": (
        "Number a (thousands)",
        "Total",
    ),
    "oasdi_reported_taxable_earnings": (
        "Taxable earnings b (millions of dollars)",
        "Total",
    ),
    "oasdi_gross_contributions": (
        "OASDI contributions c,d (millions of dollars)",
        "Total",
    ),
    "oasdi_adjusted_taxable_payroll": ("Taxable payroll b",),
    "oasdi_covered_workers": ("Covered workers a (in thousands)",),
    "oasi_net_payroll_tax_contributions": (
        "Receipts a",
        "Net payroll tax contributions b",
    ),
    "oasdi_net_payroll_tax_contributions": (
        "Receipts a",
        "Net payroll tax contributions b",
    ),
}

EXPECTED_TABLES = {
    "6.A1": (
        "Annual Statistical Supplement, 2025",
        2025,
        "Number of awards, by type of benefit, 1940\u20132024",
        "ssa_supplement_2025_6a",
    ),
    "4.A1": (
        "Annual Statistical Supplement, 2025",
        2025,
        (
            "Old-Age and Survivors Insurance Trust Fund: Receipts, "
            "expenditures, and assets, 1937\u20132024 (in millions of "
            "dollars)"
        ),
        "ssa_supplement_2025_4a",
    ),
    "4.A3": (
        "Annual Statistical Supplement, 2025",
        2025,
        (
            "Combined Old-Age and Survivors Insurance (OASI) and Disability "
            "Insurance (DI) Trust Funds: Receipts, expenditures, and assets, "
            "1957\u20132024 (in millions of dollars)"
        ),
        "ssa_supplement_2025_4a",
    ),
    "4.A5": (
        "Annual Statistical Supplement, 2025",
        2025,
        (
            "Total annual benefits paid from Old-Age and Survivors Insurance "
            "Trust Fund, by type of benefit, selected years 1937\u20132024 "
            "(in millions of dollars)"
        ),
        "ssa_supplement_2025_4a",
    ),
    "5.A4": (
        "Annual Statistical Supplement, 2025",
        2025,
        (
            "Number of beneficiaries and total monthly benefits, by trust "
            "fund and type of benefit, December 1940\u20132024, selected "
            "years"
        ),
        "ssa_supplement_2025_5a",
    ),
    "4.B11": (
        "Annual Statistical Supplement, 2025",
        2025,
        (
            "Number of workers with Social Security (OASDI) taxable earnings, "
            "amount taxable, and contributions, by type of earnings, selected "
            "years 1937\u20132024"
        ),
        "ssa_supplement_2025_4b",
    ),
    "IV.B4": (
        "2026 OASDI Trustees Report",
        2026,
        "Covered Workers and Beneficiaries, Calendar Years 1945-2100",
        "ssa_trustees_2026_lr4b4",
    ),
    "VI.G1": (
        "2026 OASDI Trustees Report",
        2026,
        (
            "Selected Economic Variables, Calendar Years 1970-2100 "
            "[GDP and taxable payroll in billions]"
        ),
        "ssa_trustees_2026_lr6g1",
    ),
}

EXPECTED_SOURCES = {
    "ssa_supplement_2025_6a": (
        "supplement2025_6a.html",
        "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/6a.html",
        "cf1cb93ab16c5447393a0efdca0b25217387a26d3413394e009e100a9faaa3a3",
        185_106,
    ),
    "ssa_supplement_2025_4a": (
        "supplement2025_4a.html",
        "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/4a.html",
        "b0c779c488105a30e7f51f75a2c812a8a3f8098b2b8030f87d3210d2536639e0",
        174_613,
    ),
    "ssa_supplement_2025_5a": (
        "supplement2025_5a.html",
        "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/5a.html",
        "d61e9484d271aec0126d8897a780668adf55f5d86f5b440a0f69782de968aa8e",
        366_249,
    ),
    "ssa_supplement_2025_4b": (
        "supplement2025_4b.html",
        "https://www.ssa.gov/policy/docs/statcomps/supplement/2025/4b.html",
        "c228920ea9d53b1e323e5933b6d9f926e3c9b609d868b549fabc40118554b449",
        488_165,
    ),
    "ssa_trustees_2026_lr4b4": (
        "trustees2026_lr4b4.html",
        "https://www.ssa.gov/oact/TR/2026/lr4b4.html",
        "40435030d154e29eb49a4e411b78253f504049eddff6e149d7e33033fb139458",
        133_558,
    ),
    "ssa_trustees_2026_lr6g1": (
        "trustees2026_lr6g1.html",
        "https://www.ssa.gov/OACT/TR/2026/lr6g1.html",
        "3b9e96be991d5a102d41ede443e157d2d1a2a928174430497dc9c3a1fa532dc0",
        226_685,
    ),
}

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_ssa_level_anchors as builder  # noqa: E402


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_bytes())


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _copy_snapshots(tmp_path: Path) -> Path:
    copied = tmp_path / "ssa_level_anchors_vintage1"
    shutil.copytree(SNAPSHOTS, copied)
    return copied


def test__anchor_artifact__is_canonical_and_sha256_pinned():
    raw = ARTIFACT.read_bytes()
    assert raw == _canonical(json.loads(raw))
    assert hashlib.sha256(raw).hexdigest() == ARTIFACT_SHA256


def test__anchor_builder__reproduces_committed_bytes():
    raw = ARTIFACT.read_bytes()
    assert builder.render() == raw
    assert builder.render() == raw


def test__anchor_artifact__pins_identity_and_complete_ordered_coverage():
    artifact = _artifact()
    assert artifact["schema_version"] == "ssa_level_anchors.v1"
    assert artifact["artifact_vintage_id"] == (
        "ssa_level_anchors.supplement2025_trustees2026.vintage1"
    )
    assert artifact["artifact_role"] == "official_context_only"
    assert artifact["year_basis"] == "calendar_year"
    assert artifact["required_calendar_years"] == list(EXPECTED_YEARS)
    assert artifact["required_series_ids"] == list(EXPECTED_SERIES_IDS)
    assert set(artifact["determinations"]) == set(EXPECTED_SERIES_IDS)

    observation_count = 0
    for series_id in EXPECTED_SERIES_IDS:
        determination = artifact["determinations"][series_id]
        assert determination["series_id"] == series_id
        assert determination["year_basis"] == "calendar_year"
        assert [
            observation["year"]
            for observation in determination["observations"]
        ] == list(EXPECTED_YEARS)
        assert determination["official_concept"]["comparison_status"] == (
            "context_only"
        )
        assert all(determination["official_concept"].values())
        observation_count += len(determination["observations"])
    assert observation_count == 120
    assert artifact["validation"]["n_observations"] == 120


def test__anchor_artifact__matches_scoping_survey_transcriptions():
    artifact = _artifact()
    observed = {
        series_id: tuple(
            row["as_published"]
            for row in artifact["determinations"][series_id]["observations"]
        )
        for series_id in EXPECTED_SERIES_IDS
    }
    assert observed == EXPECTED_AS_PUBLISHED


def test__anchor_artifact__normalizes_every_value_to_stored_unit():
    artifact = _artifact()
    for series_id, expected_unit in EXPECTED_UNITS.items():
        determination = artifact["determinations"][series_id]
        published_unit, stored_unit, scale = expected_unit
        assert (
            determination["published_unit"],
            determination["stored_unit"],
            determination["scale_multiplier"],
        ) == expected_unit
        for observation in determination["observations"]:
            assert observation["published_unit"] == published_unit
            assert observation["stored_unit"] == stored_unit
            assert observation["scale_multiplier"] == scale
            published = int(
                observation["as_published"].replace("$", "").replace(",", "")
            )
            assert type(observation["value"]) is int
            assert observation["value"] == published * scale


def test__anchor_artifact__pins_cell_status_law():
    artifact = _artifact()
    for series_id in EXPECTED_SERIES_IDS:
        statuses = tuple(
            observation["source_status"]
            for observation in artifact["determinations"][series_id][
                "observations"
            ]
        )
        if series_id in {
            "retired_worker_benefits_paid_estimated_allocation",
            "oasi_benefits_paid_estimated_allocation",
        }:
            assert statuses == ("estimated_allocation",) * 8
        elif series_id in {
            "oasdi_workers_with_taxable_earnings",
            "oasdi_reported_taxable_earnings",
            "oasdi_gross_contributions",
        }:
            assert statuses == ("historical",) * 6 + ("preliminary",) * 2
        else:
            assert statuses == ("historical",) * 8


def test__anchor_artifact__pins_exact_header_paths():
    artifact = _artifact()
    for series_id, column_path in EXPECTED_COLUMN_PATHS.items():
        observations = artifact["determinations"][series_id]["observations"]
        assert {
            tuple(observation["source_column_header_path"])
            for observation in observations
        } == {column_path}
        for observation in observations:
            year = observation["year"]
            if series_id in {
                "retired_worker_december_current_payment_stock",
                "oasi_december_current_payment_stock",
                "oasdi_december_current_payment_stock",
            }:
                expected_row = ("Number", str(year))
            elif series_id in {
                "oasdi_adjusted_taxable_payroll",
                "oasdi_covered_workers",
            }:
                expected_row = ("Historical data:", str(year))
            elif series_id in {
                "oasdi_workers_with_taxable_earnings",
                "oasdi_reported_taxable_earnings",
                "oasdi_gross_contributions",
            } and year in {2021, 2022}:
                expected_row = (f"{year} e",)
            else:
                expected_row = (str(year),)
            assert tuple(observation["source_row_header_path"]) == expected_row


def test__anchor_artifact__pins_exact_source_table_titles():
    artifact = _artifact()
    observed_tables = {}
    for determination in artifact["determinations"].values():
        table = determination["source_table"]
        observed = (
            table["publication"],
            table["edition_or_report_year"],
            table["table_title"],
            table["source_document_id"],
        )
        assert observed == EXPECTED_TABLES[table["table_id"]]
        observed_tables[table["table_id"]] = observed
        assert table["publisher"] == "Social Security Administration"
    assert observed_tables == EXPECTED_TABLES


def test__anchor_artifact__binds_sources_to_capture_manifest():
    artifact = _artifact()
    documents = artifact["source_documents"]
    assert set(documents) == set(EXPECTED_SOURCES)
    timestamp = "2026-07-27T13:02:54Z"
    for document_id, expected in EXPECTED_SOURCES.items():
        filename, url, sha256, size = expected
        document = documents[document_id]
        assert document["official_url"] == url
        assert document["sha256"] == sha256
        assert document["size_bytes"] == size
        assert document["retrieval_timestamp"] == timestamp
        assert document["committed_raw_snapshot_path"] == (
            "data/external/snapshots/ssa_level_anchors_vintage1/" f"{filename}"
        )
        assert document["capture_manifest_path"] == (
            "data/external/snapshots/ssa_level_anchors_vintage1/"
            "capture_manifest.txt"
        )
        assert document["source_hash_basis"] == (
            "sha256 of exact committed raw snapshot bytes"
        )
        assert document["capture_manifest_entry"] == (
            f"{timestamp} {sha256} {size} {filename}"
        )
        assert hashlib.sha256(
            (SNAPSHOTS / filename).read_bytes()
        ).hexdigest() == (sha256)
        assert (SNAPSHOTS / filename).stat().st_size == size


def test__anchor_artifact__verified_against_denies_concept_equivalence():
    artifact = _artifact()
    statements = {
        observation["verified_against"]
        for determination in artifact["determinations"].values()
        for observation in determination["observations"]
    }
    assert statements == {
        (
            "Exact source-cell transcription only; this does not verify "
            "conceptual equivalence."
        )
    }


def test__builder__rejects_source_drift_before_parsing(tmp_path, monkeypatch):
    copied = _copy_snapshots(tmp_path)
    source = copied / "trustees2026_lr6g1.html"
    changed = bytearray(source.read_bytes())
    changed[-1] ^= 1
    source.write_bytes(changed)
    monkeypatch.setattr(builder, "SNAPSHOT_DIR", copied)

    def parse_must_not_run(*_args, **_kwargs):
        raise AssertionError(
            "HTML parsing ran before all source hashes passed"
        )

    monkeypatch.setattr(builder, "_parse_tables", parse_must_not_run)
    with pytest.raises(ValueError, match="source-byte drift"):
        builder.build()


@pytest.mark.parametrize("table_id", ("4.A5", "4.B11"))
def test__builder__rejects_missing_status_evidence(table_id, monkeypatch):
    tables = dict(builder.TABLE_SPECS)
    tables[table_id] = replace(tables[table_id], status_evidence=None)
    monkeypatch.setattr(builder, "TABLE_SPECS", tables)
    with pytest.raises(ValueError, match="status evidence"):
        builder.build()


def test__builder__rejects_capture_manifest_drift(tmp_path, monkeypatch):
    copied = _copy_snapshots(tmp_path)
    manifest = copied / "capture_manifest.txt"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    monkeypatch.setattr(builder, "SNAPSHOT_DIR", copied)
    with pytest.raises(ValueError, match="source manifest drift"):
        builder.build()


def test__builder__rejects_colspan_collapsed_value_cells(monkeypatch):
    entries, raw_by_document_id = builder.read_verified_snapshots()
    attacked_entries = dict(entries)
    attacked_raw_by_document_id = dict(raw_by_document_id)
    document_id = "ssa_supplement_2025_6a"
    raw = attacked_raw_by_document_id[document_id]
    distinct_cells = (
        b"        <td>5,440,023</td>\r\n"
        b"        <td>2,838,988</td>"
    )
    collapsed_cell = b'        <td colspan="2">2,838,988</td>'
    assert raw.count(distinct_cells) == 1
    attacked_raw = raw.replace(distinct_cells, collapsed_cell)
    attacked_raw_by_document_id[document_id] = attacked_raw

    # Model a prospective capture whose snapshot and manifest entry were
    # deliberately re-pinned together, so the source hash gate has passed.
    original_entry = attacked_entries[document_id]
    attacked_sha256 = hashlib.sha256(attacked_raw).hexdigest()
    assert attacked_sha256 == (
        "94e78a97f7921391fbe77ef4616796f09345d546af320fee14e094c9360c0ac7"
    )
    attacked_literal_entry = (
        f"{original_entry.retrieval_timestamp} {attacked_sha256} "
        f"{len(attacked_raw)} {original_entry.filename}"
    )
    attacked_entries[document_id] = replace(
        original_entry,
        sha256=attacked_sha256,
        size_bytes=len(attacked_raw),
        literal_entry=attacked_literal_entry,
    )

    monkeypatch.setattr(
        builder,
        "read_verified_snapshots",
        lambda: (attacked_entries, attacked_raw_by_document_id),
    )
    with pytest.raises(ValueError, match="unique physical 1x1 data cell"):
        builder.build()


def test__builder__rejects_required_series_reorder(monkeypatch):
    specs = builder.SERIES_SPECS
    monkeypatch.setattr(
        builder,
        "SERIES_SPECS",
        (specs[1], specs[0], *specs[2:]),
    )
    with pytest.raises(ValueError, match="reordered"):
        builder.build()


def test__builder__rejects_locator_selecting_a_different_cell(monkeypatch):
    specs = builder.SERIES_SPECS
    wrong = replace(specs[0], column_header_path=("All benefits a",))
    monkeypatch.setattr(builder, "SERIES_SPECS", (wrong, *specs[1:]))
    with pytest.raises(ValueError, match="canonical determinations sha256"):
        builder.build()


def test__builder__rejects_generated_trustees_identity(monkeypatch):
    sources = list(builder.SOURCE_DOCUMENT_SPECS)
    sources[-1] = replace(
        sources[-1],
        filename="trustees2026_generated.html",
    )
    monkeypatch.setattr(builder, "SOURCE_DOCUMENT_SPECS", tuple(sources))
    with pytest.raises(ValueError, match="Trustees identities"):
        builder.build()


def test__validator__rejects_status_authority_drift():
    artifact = _artifact()
    preliminary = copy.deepcopy(artifact)
    preliminary["determinations"]["oasdi_gross_contributions"]["observations"][
        -1
    ]["source_status"] = "historical"
    with pytest.raises(ValueError, match="status"):
        builder._validate_artifact(preliminary)

    estimated = copy.deepcopy(artifact)
    estimated["determinations"][
        "retired_worker_benefits_paid_estimated_allocation"
    ]["observations"][0]["source_status"] = "historical"
    with pytest.raises(ValueError, match="status"):
        builder._validate_artifact(estimated)


def test__validator__rejects_missing_cell_metadata_and_concept_claim():
    artifact = _artifact()
    series_id = "retired_worker_awards"

    missing = copy.deepcopy(artifact)
    missing["determinations"][series_id]["observations"][0]["source_url"] = ""
    with pytest.raises(ValueError, match="missing source_url"):
        builder._validate_artifact(missing)

    claim = copy.deepcopy(artifact)
    claim["determinations"][series_id]["observations"][0][
        "verified_against"
    ] = "Conceptually equivalent."
    with pytest.raises(ValueError, match="conceptual equivalence"):
        builder._validate_artifact(claim)


def test__validator__rejects_source_build_and_validation_metadata_drift():
    artifact = _artifact()
    mutations = (
        lambda value: value["source_documents"][
            "ssa_supplement_2025_6a"
        ].__setitem__("sha256", "0" * 64),
        lambda value: value["build"].__setitem__(
            "capture_manifest_sha256", "0" * 64
        ),
        lambda value: value["validation"].__setitem__(
            "status_law_exact", False
        ),
    )
    for mutate in mutations:
        changed = copy.deepcopy(artifact)
        mutate(changed)
        with pytest.raises(ValueError):
            builder._validate_artifact(changed)


def test__validator__rejects_identity_and_year_coverage_drift():
    artifact = _artifact()

    reordered = copy.deepcopy(artifact)
    reordered["required_series_ids"][:2] = reversed(
        reordered["required_series_ids"][:2]
    )
    with pytest.raises(ValueError, match="required series IDs"):
        builder._validate_artifact(reordered)

    extra = copy.deepcopy(artifact)
    extra["determinations"]["extra_series"] = {}
    with pytest.raises(ValueError, match="determination keys"):
        builder._validate_artifact(extra)

    years = copy.deepcopy(artifact)
    observations = years["determinations"]["retired_worker_awards"][
        "observations"
    ]
    observations[0], observations[1] = observations[1], observations[0]
    with pytest.raises(ValueError, match="years"):
        builder._validate_artifact(years)


def test__validator__rejects_each_required_cell_field_class():
    artifact = _artifact()
    series_id = "retired_worker_awards"
    mutations = (
        lambda row: row.__setitem__("as_published", ""),
        lambda row: row.__setitem__("published_unit", ""),
        lambda row: row.__setitem__("stored_unit", ""),
        lambda row: row.__setitem__("scale_multiplier", 2),
        lambda row: row.__setitem__("source_status", ""),
        lambda row: row.__setitem__("source_table_id", ""),
        lambda row: row.__setitem__("source_row_header_path", []),
        lambda row: row.__setitem__("source_column_header_path", []),
    )
    for mutate in mutations:
        changed = copy.deepcopy(artifact)
        row = changed["determinations"][series_id]["observations"][0]
        mutate(row)
        with pytest.raises(ValueError):
            builder._validate_artifact(changed)
