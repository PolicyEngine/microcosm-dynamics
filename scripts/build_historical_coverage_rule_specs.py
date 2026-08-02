#!/usr/bin/env python3
"""Build the fail-closed historical-coverage legal registration audit.

The registered external capture contains source candidates for the future
``historical_coverage_rule_specs.v1`` legal-source manifest.  It does not yet
contain enough authority to emit that registry: the official PSID source-field
inventory is absent, one represented GovInfo PDF is an HTML error response,
and the V-B1/V-B4 rank-1 chains retain enumerated gaps.  This module therefore
authenticates and classifies the usable source bytes, emits a deterministic
registration-required audit, and makes the production builder abort.

No network access, filename-only lookup, or repository snapshot is used.
Every source read resolves through the registered staging root and an exact
capture-manifest row, then verifies full-file size and SHA-256 before trusting
the bytes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

__all__ = [
    "RegistrationRequiredError",
    "build_registration_required_audit",
    "build_registry",
    "canonical_json_bytes",
    "legal_rule_input_identity",
    "rejected_source_documents",
    "render_audit",
    "source_document_candidates",
    "strict_json_loads",
    "validate_registration_required_audit",
    "validate_registration_required_audit_structure",
    "verify_design_binding",
]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAPTURE_ROOT = Path(
    "~/PolicyEngine/psid-data/legal-capture-staging"
).expanduser()
CAPTURE_ROOT_ID = "psid_external_staging_root"
CAPTURE_RELATIVE_PATH = "legal-capture-staging"
REPO_AUTHORITY_LOCATOR_ID = "psid_external_staging_law"
STAGING_IDENTITY = {
    "staging_root_id": CAPTURE_ROOT_ID,
    "relative_capture_path": CAPTURE_RELATIVE_PATH,
    "absolute_paths_serialized": False,
    "repo_authority_locator_id": REPO_AUTHORITY_LOCATOR_ID,
}
CAPTURE_MANIFEST_FILENAME = "capture_manifest.tsv"
OUT_PATH = (
    ROOT
    / "data"
    / "external"
    / "historical_coverage_legal_registration_required_v1.json"
)

SCHEMA_VERSION = "historical_coverage_legal_registration_required.v1"
ARTIFACT_ID = SCHEMA_VERSION
TARGET_REGISTRY_PATH = "data/registries/historical_coverage_rule_specs_v1.json"
TARGET_REGISTRY_SCHEMA_VERSION = "historical_coverage_rule_specs.v1"
TARGET_REGISTRY_ARTIFACT_VINTAGE_ID = TARGET_REGISTRY_SCHEMA_VERSION
SOURCE_MANIFEST_SCHEMA_VERSION = "historical_coverage_legal_source_manifest.v1"
CANONICALIZATION = "python-json-sort-keys-compact-ascii-no-nan-lf-v1"
FAILURE_DISPOSITION = "abort_registration"

DESIGN_PATH = "docs/design/covered_earnings_correction.md"
DESIGN_RATIFICATION_COMMIT = "985be84fdeec70ffd20aa1e60dec7d300b7a555b"
DESIGN_REVISION = 7
DESIGN_BLOB_SHA256 = (
    "8f90dd1aee59e6857418d2a73b617e5cb3991eba3a237a78303586a8c2a9debc"
)

EXPECTED_CAPTURE_MANIFEST_SIZE = 18_835
EXPECTED_CAPTURE_MANIFEST_SHA256 = (
    "58951b038ac6bc5122952e5db8d76e3e78572b8c1bac403d2c0b561af16b68ac"
)
EXPECTED_CAPTURE_ROW_COUNT = 112
EXPECTED_DECLARED_SOURCE_BYTE_SIZE = 1_750_563_108
EXPECTED_SOURCE_DOCUMENT_CANDIDATE_COUNT = 111
EXPECTED_REJECTED_SOURCE_DOCUMENT_COUNT = 1
REJECTED_CAPTURE_FILENAME = "statute104-1388-469.pdf"

SOURCE_DOCUMENT_FIELDS = (
    "source_document_id",
    "manifest_position",
    "locator",
    "retrieved_at_utc",
    "source_url",
    "media_type",
    "byte_size",
    "sha256",
    "issuing_authority",
    "authority_class",
)
REJECTED_SOURCE_DOCUMENT_FIELDS = (
    "source_document_id",
    "manifest_position",
    "locator",
    "retrieved_at_utc",
    "source_url",
    "declared_media_type",
    "observed_media_type",
    "byte_size",
    "sha256",
    "issuing_authority",
    "authority_class",
    "rejection_code",
    "rejection_detail",
)
REGISTRY_TOP_LEVEL_FIELDS = (
    "schema_version",
    "artifact_id",
    "artifact_vintage_id",
    "source_inventory_identity",
    "legal_source_manifest",
    "rule_domain",
    "ordered_rule_ids",
    "rows",
    "row_count",
    "row_keyset_sha256",
    "rows_sha256",
    "rule_interval_partitions",
    "rule_interval_partition_count",
    "rule_interval_partition_sha256",
    "canonical_order",
    "integrity",
    "status",
)
AUTHORITY_CLASSES = (
    "federal_statute",
    "federal_regulation",
    "executed_section_218_agreement_or_modification",
    "state_enactment_or_official_determination",
    "ssa_administering_material",
    "irs_administering_material",
    "opm_administering_material",
    "rrb_administering_material",
    "corroborating_only",
)
AUTHORITY_RANK_BY_CLASS: dict[str, int | None] = {
    "federal_statute": 1,
    "federal_regulation": 1,
    "executed_section_218_agreement_or_modification": 1,
    "state_enactment_or_official_determination": 1,
    "ssa_administering_material": 2,
    "irs_administering_material": 2,
    "opm_administering_material": 2,
    "rrb_administering_material": 2,
    "corroborating_only": None,
}

_US_CODE_ISSUER = (
    "Office of the Law Revision Counsel, U.S. House of Representatives"
)
_CONGRESS_ISSUER = "United States Congress"
_SSA_ISSUER = "Social Security Administration"
_HHS_SSA_ISSUER = (
    "Social Security Administration, U.S. Department of Health and Human "
    "Services"
)
_IRS_ISSUER = "Internal Revenue Service, U.S. Department of the Treasury"
_OACT_ISSUER = "Office of the Chief Actuary, Social Security Administration"

# This is a reviewed, closed filename-to-issuer/class table.  Grouping equal
# values keeps it readable; the filenames themselves remain explicit and no
# classification is inferred from a URL, suffix, or filename pattern.
REVIEWED_SOURCE_METADATA: dict[str, tuple[str, str]] = {
    **{
        filename: (_US_CODE_ISSUER, "federal_statute")
        for filename in (
            "uscode42-410.pdf",
            "uscode42-411.pdf",
            "uscode42-418.pdf",
            "uscode42-430.pdf",
            "uscode26-1402.pdf",
            "uscode26-3231.pdf",
            "uscode5-8331.pdf",
            "uscode5-8334.pdf",
            "uscode5-8401.pdf",
            "uscode5-8402.pdf",
        )
    },
    **{
        filename: (_CONGRESS_ISSUER, "federal_statute")
        for filename in (
            "statute64-514.pdf",
            "statute68-1052.pdf",
            "statute70-807.pdf",
            "statute81-821.pdf",
            "statute103-2474.pdf",
            "statute108-1464.pdf",
            "STATUTE-97-Pg65.pdf",
            "STATUTE-98-Pg494.pdf",
            "STATUTE-100-Pg514.pdf",
            "PLAW-105publ277.pdf",
            "statute-plaw-92-5-85Stat10.pdf",
            "statute-plaw-92-336-86Stat418.pdf",
            "statute-plaw-92-603-86Stat1353.pdf",
            "statute-plaw-93-66-87Stat153.pdf",
            "statute-plaw-93-233-87Stat953.pdf",
            "statute-plaw-93-368-88Stat422.pdf",
            "statute-plaw-94-92-89Stat465.pdf",
            "statute-plaw-94-455-90Stat1707.pdf",
            "statute-plaw-95-216-91Stat1535.pdf",
            "statute-plaw-95-600-92Stat2942.pdf",
            "statute-plaw-95-615-92Stat3100.pdf",
            "statute-plaw-96-222-94Stat223.pdf",
            "statute-plaw-97-34-95Stat194.pdf",
            "statute-plaw-97-248-96Stat559.pdf",
            "statute-plaw-99-272-100Stat315.pdf",
            "statute-plaw-99-509-100Stat1971.pdf",
            "statute-plaw-99-514-100Stat2915.pdf",
            "statute-plaw-100-203-101Stat1330.pdf",
            "statute-plaw-100-647-102Stat3488.pdf",
            "statute-plaw-101-508-104Stat1388.pdf",
        )
    },
    **{
        filename: (_SSA_ISSUER, "federal_statute")
        for filename in (
            "ssact-0209.html",
            "ssact-0210.html",
            "ssact-0211.html",
            "ssact-0218.html",
            "ssact-0230.html",
        )
    },
    **{
        filename: (_SSA_ISSUER, "federal_regulation")
        for filename in (
            "CFR-2025-t20-v2-p404-subpartM.pdf",
            "CFR-2025-t20-v2-p404-subpartK.pdf",
            "cfr20-404-1096.html",
            "FR-1985-09-09.pdf",
            "FR-1987-03-17.pdf",
            "FR-1988-08-29.pdf",
            "FR-1992-09-24.pdf",
        )
    },
    "FR-1980-03-27.pdf": (_HHS_SSA_ISSUER, "federal_regulation"),
    **{
        filename: (_IRS_ISSUER, "federal_regulation")
        for filename in (
            "CFR-2025-t26-v17-part31.pdf",
            "FR-1991-06-28.pdf",
            "FR-1991-08-14.pdf",
        )
    },
    **{
        filename: (_OACT_ISSUER, "ssa_administering_material")
        for filename in (
            "oact-CovThresh.html",
            "oact-covthreshdet.html",
        )
    },
    **{
        filename: (_SSA_ISSUER, "ssa_administering_material")
        for filename in (
            "comp2-F099-272.html",
            "poms-SL30001301.html",
            "poms-SL10001130.html",
            "poms-SL20001201.html",
        )
    },
    **{
        filename: (_IRS_ISSUER, "irs_administering_material")
        for filename in (
            "f1040sc--1968.pdf",
            "f1040sf--1968.pdf",
            "i1040--1968.pdf",
            "f1040sse--1969.pdf",
            "i1040--1969.pdf",
            "f1040sse--1970.pdf",
            "i1040--1970.pdf",
            "f1040sse--1971.pdf",
            "i1040--1971.pdf",
            "f1040sse--1972.pdf",
            "i1040--1972.pdf",
            "f1040sse--1973.pdf",
            "i1040--1973.pdf",
            "f1040sse--1974.pdf",
            "i1040--1974.pdf",
            "f1040sse--1975.pdf",
            "i1040--1975.pdf",
            "f1040sse--1976.pdf",
            "i1040--1976.pdf",
            "f1040sse--1977.pdf",
            "i1040--1977.pdf",
            "f1040sse--1978.pdf",
            "i1040--1978.pdf",
            "f1040sse--1979.pdf",
            "i1040--1979.pdf",
            "f1040sse--1980.pdf",
            "i1040--1980.pdf",
            "f1040sse--1981.pdf",
            "i1040--1981.pdf",
            "f1040sse--1982.pdf",
            "i1040--1982.pdf",
            "f1040sse--1983.pdf",
            "i1040--1983.pdf",
            "f1040sse--1984.pdf",
            "i1040--1984.pdf",
            "f1040sse--1985.pdf",
            "i1040--1985.pdf",
            "f1040sse--1986.pdf",
            "i1040--1986.pdf",
            "f1040sse--1987.pdf",
            "i1040--1987.pdf",
            "f1040sse--1988.pdf",
            "i1040--1988.pdf",
            "f1040sse--1989.pdf",
            "i1040--1989.pdf",
        )
    },
    **{
        filename: (_SSA_ISSUER, "corroborating_only")
        for filename in (
            "supp2024-oasdi.pdf",
            "supp2024-2a1-2a7.pdf",
            "sspus1997-social-insurance.html",
            "supplement-index.html",
        )
    },
}
REJECTED_SOURCE_METADATA = {
    REJECTED_CAPTURE_FILENAME: (_CONGRESS_ISSUER, "federal_statute")
}

DEPENDENCY_ROWS: tuple[dict[str, Any], ...] = (
    {
        "dependency_id": "official_psid_source_field_inventory",
        "required_path": (
            "data/external/"
            "psid_covered_earnings_source_field_inventory_v1.json"
        ),
        "required_artifact_id": (
            "psid_covered_earnings_source_field_inventory.v1"
        ),
        "required_schema_version": "psid_source_field_inventory.v1",
        "observed_status": "not_emitted_registration_required",
        "required_for": [
            "historical_coverage_rule_domain.v1",
            "affected_inventory_keys",
            "direct_law_fact_binding.v1",
            "optional_row_consequences",
        ],
        "failure_code": "official_inventory_absent",
    },
)

SOURCE_GAP_ROWS: tuple[dict[str, Any], ...] = (
    {
        "gap_id": "v_b1_missing_executed_section_218_instrument_universe",
        "claim_id": "V-B1",
        "status_family": "section_218_and_mandatory_state_local",
        "authority_rank": 1,
        "status": "registration_required",
        "missing_authority": (
            "No complete source-authenticated universe of executed state "
            "Section 218 agreements, modifications, corrections, "
            "dissolutions, effective-date approvals, referenda or governor "
            "certifications, and required state-law determinations is "
            "present."
        ),
        "consequence": "abort_registration",
    },
    {
        "gap_id": "v_b4_missing_annual_base_determination_bytes",
        "claim_id": "V-B4",
        "status_family": "historical_seca",
        "authority_rank": 1,
        "status": "registration_required",
        "missing_authority": (
            "No complete contemporaneous Federal Register determination "
            "byte chain establishes formula-set contribution and benefit "
            "bases for 1975-1978 and 1982-1989; annual IRS forms are rank-2 "
            "operational evidence only."
        ),
        "consequence": "abort_registration",
    },
)

EVIDENCE_CONSTRAINT_ROWS: tuple[dict[str, Any], ...] = (
    {
        "constraint_id": "v_b4_se_aggregation_domain_unresolved",
        "claim_id": "V-B4",
        "status_family": "historical_seca",
        "authority_rank": 2,
        "status": "registration_required",
        "evidence_finding": (
            "The annual Schedule SE instructions require taxpayer-year "
            "aggregation and cross-business farm/nonfarm loss offsets before "
            "the threshold test."
        ),
        "required_resolution": (
            "The official inventory and SE aggregation registry must prove "
            "that every eligible component collapses to one taxpayer-year "
            "unit; per-group flooring or thresholding is unsupported."
        ),
        "consequence": "abort_registration",
    },
    {
        "constraint_id": "v_b4_optional_method_inputs_unavailable",
        "claim_id": "V-B4",
        "status_family": "historical_seca",
        "authority_rank": 2,
        "status": "registration_required",
        "evidence_finding": (
            "Every 1968-1989 annual return permits a conditional farm "
            "optional method, and 1973-1989 returns also permit a conditional "
            "nonfarm optional method."
        ),
        "required_resolution": (
            "Complete transforms require official-inventory gross "
            "farm/nonfarm income, election, prior-year SE, and lifetime-use "
            "facts."
        ),
        "consequence": "abort_registration",
    },
    {
        "constraint_id": "v_b4_electing_church_threshold_path_incomplete",
        "claim_id": "V-B4",
        "status_family": "historical_seca",
        "authority_rank": 1,
        "status": "registration_required",
        "evidence_finding": (
            "Staged P.L. 98-369 section 2603(c)-(e), 98 Stat. 1128-1130, "
            "establishes a 1984-1989 electing-church path under which the "
            "ordinary $400 rule does not apply and remuneration below $100 "
            "is excluded."
        ),
        "required_resolution": (
            "The official inventory must supply church election, "
            "remuneration, and HI-only/OASDI wage-coordination facts; a "
            "blanket $400 transform is incomplete."
        ),
        "consequence": "abort_registration",
    },
)

RULE_REGISTRY_CENSUS_ROWS: tuple[dict[str, Any], ...] = (
    {
        "claim_scope": "V-B1",
        "status_family_scope": "section_218_and_mandatory_state_local",
        "authority_rank": 1,
        "authority_status": "not_emitted_registration_required",
        "rule_row_count": 0,
    },
    {
        "claim_scope": "V-B1",
        "status_family_scope": "section_218_and_mandatory_state_local",
        "authority_rank": 2,
        "authority_status": "not_emitted_registration_required",
        "rule_row_count": 0,
    },
    {
        "claim_scope": "V-B4",
        "status_family_scope": "historical_seca",
        "authority_rank": 1,
        "authority_status": "not_emitted_registration_required",
        "rule_row_count": 0,
    },
    {
        "claim_scope": "V-B4",
        "status_family_scope": "historical_seca",
        "authority_rank": 2,
        "authority_status": "not_emitted_registration_required",
        "rule_row_count": 0,
    },
    {
        "claim_scope": "direct_only_optional",
        "status_family_scope": "twelve_optional_families",
        "authority_rank": None,
        "authority_status": "not_emitted_inventory_dependency",
        "rule_row_count": 0,
    },
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RFC3339_SECONDS_UTC = re.compile(
    r"^[0-9]{4}-(?:0[1-9]|1[0-2])-"
    r"(?:0[1-9]|[12][0-9]|3[01])T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$"
)


class RegistrationRequiredError(RuntimeError):
    """The ratified production registry cannot yet be emitted."""

    def __init__(
        self,
        dependency_ids: Sequence[str],
        source_gap_ids: Sequence[str],
        evidence_constraint_ids: Sequence[str] = (),
    ) -> None:
        self.dependency_ids = tuple(dependency_ids)
        self.source_gap_ids = tuple(source_gap_ids)
        self.evidence_constraint_ids = tuple(evidence_constraint_ids)
        self.registration_required_ids = (
            *self.dependency_ids,
            *self.source_gap_ids,
            *self.evidence_constraint_ids,
        )
        super().__init__(
            "historical_coverage_rule_specs.v1 registration required: "
            + ", ".join(self.registration_required_ids)
        )


def _assert_json_value(value: Any, where: str = "$") -> None:
    """Reject Python values outside the strict JSON value model."""

    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is float:
        raise ValueError(f"{where} contains a forbidden floating-point value")
    if type(value) is list:
        for index, item in enumerate(value):
            _assert_json_value(item, f"{where}/{index}")
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{where} contains a non-string object key")
            _assert_json_value(item, f"{where}/{key}")
        return
    raise ValueError(
        f"{where} contains a non-JSON value of type {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return §19 canonical JSON bytes, rejecting every float value."""

    _assert_json_value(value)
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def strict_json_loads(raw: bytes, label: str = "JSON input") -> Any:
    """Strict-parse and canonical-round-trip a §19 JSON byte string."""

    if type(raw) is not bytes:
        raise ValueError(f"{label} must be bytes")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    def reject_float(token: str) -> NoReturn:
        raise ValueError(f"{label} contains forbidden float token {token!r}")

    def reject_constant(token: str) -> NoReturn:
        raise ValueError(
            f"{label} contains non-finite constant token {token!r}"
        )

    def canonical_integer(token: str) -> int:
        if token == "-0":
            raise ValueError(f"{label} contains noncanonical integer -0")
        return int(token)

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ValueError(f"{label} is not strict UTF-8") from error
    if text.startswith("\ufeff"):
        raise ValueError(f"{label} contains a leading U+FEFF BOM")
    try:
        value = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_float=reject_float,
            parse_int=canonical_integer,
            parse_constant=reject_constant,
        )
    except (ValueError, OverflowError, RecursionError) as error:
        raise ValueError(
            f"{label} is not uniquely parseable strict JSON"
        ) from error
    if raw != canonical_json_bytes(value):
        raise ValueError(f"{label} bytes are not canonical")
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(
    value: object, fields: Sequence[str], where: str
) -> Mapping[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{where} must be a JSON object")
    missing = set(fields) - set(value)
    extra = set(value) - set(fields)
    if missing or extra:
        raise ValueError(
            f"{where} has wrong fields; "
            f"missing={sorted(missing)!r}, extra={sorted(extra)!r}"
        )
    return value


def _json_int(value: object, where: str, *, positive: bool = False) -> int:
    if type(value) is not int or (positive and value <= 0) or value < 0:
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{where} must be a {qualifier} JSON integer")
    return value


def _nonempty_string(value: object, where: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{where} must be a nonempty string")
    return value


def verify_design_binding() -> dict[str, Any]:
    """Require the live, HEAD, and ratification design bytes to be revision 7."""

    ancestry = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            DESIGN_RATIFICATION_COMMIT,
            "HEAD",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise ValueError("revision-7 design ratification is not an ancestor")
    worktree_bytes = (ROOT / DESIGN_PATH).read_bytes()
    head_bytes = subprocess.run(
        ["git", "show", f"HEAD:{DESIGN_PATH}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    ratified_bytes = subprocess.run(
        ["git", "show", f"{DESIGN_RATIFICATION_COMMIT}:{DESIGN_PATH}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    if not (worktree_bytes == head_bytes == ratified_bytes):
        raise ValueError("covered-earnings design differs from revision 7")
    if _sha256(ratified_bytes) != DESIGN_BLOB_SHA256:
        raise ValueError("covered-earnings revision-7 design digest drift")
    return {
        "path": DESIGN_PATH,
        "ratification_commit": DESIGN_RATIFICATION_COMMIT,
        "revision": DESIGN_REVISION,
        "blob_sha256": DESIGN_BLOB_SHA256,
    }


def _full_file_locator(filename: str, raw: bytes) -> dict[str, Any]:
    digest = _sha256(raw)
    return {
        "location_type": "full_file_byte_range",
        "filename": filename,
        "full_file_sha256": digest,
        "size_bytes": len(raw),
        "byte_start": 0,
        "byte_end": len(raw),
        "range_sha256": digest,
    }


def _verified_staged_file(
    capture_root: Path,
    filename: str,
    *,
    expected_size: int,
    expected_sha256: str,
) -> bytes:
    path_token = PurePosixPath(filename)
    if (
        path_token.name != filename
        or path_token.is_absolute()
        or ".." in path_token.parts
        or filename in {"", ".", ".."}
    ):
        raise ValueError(f"unsafe staged filename {filename!r}")
    if not capture_root.is_dir() or capture_root.is_symlink():
        raise ValueError("legal capture root is unavailable or symlinked")
    path = capture_root / filename
    if not path.is_file() or path.is_symlink():
        raise ValueError(
            f"{filename} is unavailable, nonregular, or symlinked"
        )
    raw = path.read_bytes()
    if len(raw) != expected_size or _sha256(raw) != expected_sha256:
        raise ValueError(f"{filename} staged identity mismatch")
    return raw


def _capture_manifest_rows(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise ValueError("capture manifest is not strict UTF-8") from error
    if text.startswith("\ufeff") or not text.endswith("\n"):
        raise ValueError("capture manifest BOM or terminal-LF drift")
    rows: list[dict[str, Any]] = []
    for position, line in enumerate(text.splitlines(), start=1):
        parts = line.split("\t")
        if len(parts) != 5:
            raise ValueError(f"capture manifest row {position} grammar drift")
        retrieved_at_utc, sha256, byte_size_token, filename, source_url = parts
        if _RFC3339_SECONDS_UTC.fullmatch(retrieved_at_utc) is None:
            raise ValueError(
                f"capture manifest row {position} timestamp drift"
            )
        if _HEX64.fullmatch(sha256) is None:
            raise ValueError(f"capture manifest row {position} digest drift")
        if not byte_size_token.isascii() or not byte_size_token.isdecimal():
            raise ValueError(
                f"capture manifest row {position} size grammar drift"
            )
        if len(byte_size_token) > 1 and byte_size_token.startswith("0"):
            raise ValueError(
                f"capture manifest row {position} size is noncanonical"
            )
        byte_size = int(byte_size_token)
        if byte_size <= 0:
            raise ValueError(
                f"capture manifest row {position} size is not positive"
            )
        if (
            PurePosixPath(filename).name != filename
            or filename in {".", ".."}
            or not filename.endswith((".pdf", ".html"))
        ):
            raise ValueError(f"capture manifest row {position} filename drift")
        if not source_url.startswith("https://"):
            raise ValueError(f"capture manifest row {position} URL drift")
        rows.append(
            {
                "manifest_position": position,
                "retrieved_at_utc": retrieved_at_utc,
                "sha256": sha256,
                "byte_size": byte_size,
                "filename": filename,
                "source_url": source_url,
            }
        )
    if len(rows) != EXPECTED_CAPTURE_ROW_COUNT:
        raise ValueError("capture manifest row-count drift")
    if len({row["filename"] for row in rows}) != len(rows):
        raise ValueError("capture manifest filename duplication")
    if len({row["sha256"] for row in rows}) != len(rows):
        raise ValueError("capture manifest digest duplication")
    if (
        sum(row["byte_size"] for row in rows)
        != EXPECTED_DECLARED_SOURCE_BYTE_SIZE
    ):
        raise ValueError("capture manifest declared-byte total drift")
    expected_metadata_names = set(REVIEWED_SOURCE_METADATA) | set(
        REJECTED_SOURCE_METADATA
    )
    if {row["filename"] for row in rows} != expected_metadata_names:
        raise ValueError("capture manifest reviewed-metadata domain drift")
    return rows


def _declared_media_type(filename: str) -> str:
    if filename.endswith(".pdf"):
        return "application/pdf"
    if filename.endswith(".html"):
        return "text/html"
    raise ValueError(f"unregistered source suffix for {filename}")


def _observed_media_type(raw: bytes) -> str:
    if raw.startswith(b"%PDF-"):
        return "application/pdf"
    prefix = raw[:4096].decode("utf-8", errors="ignore").lstrip()
    if re.match(r"(?is)^(?:<!doctype\s+html\b|<html\b)", prefix):
        return "text/html"
    return "application/octet-stream"


def _verified_capture(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_raw = _verified_staged_file(
        capture_root,
        CAPTURE_MANIFEST_FILENAME,
        expected_size=EXPECTED_CAPTURE_MANIFEST_SIZE,
        expected_sha256=EXPECTED_CAPTURE_MANIFEST_SHA256,
    )
    manifest_rows = _capture_manifest_rows(manifest_raw)
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in manifest_rows:
        filename = row["filename"]
        raw = _verified_staged_file(
            capture_root,
            filename,
            expected_size=row["byte_size"],
            expected_sha256=row["sha256"],
        )
        locator = _full_file_locator(filename, raw)
        declared_media_type = _declared_media_type(filename)
        observed_media_type = _observed_media_type(raw)
        source_document_id = f"legal-source:{row['sha256']}"
        if declared_media_type != observed_media_type:
            if filename != REJECTED_CAPTURE_FILENAME:
                raise ValueError(
                    f"{filename} has an unreviewed media-type mismatch"
                )
            issuer, authority_class = REJECTED_SOURCE_METADATA[filename]
            rejected.append(
                {
                    "source_document_id": source_document_id,
                    "manifest_position": row["manifest_position"],
                    "locator": locator,
                    "retrieved_at_utc": row["retrieved_at_utc"],
                    "source_url": row["source_url"],
                    "declared_media_type": declared_media_type,
                    "observed_media_type": observed_media_type,
                    "byte_size": row["byte_size"],
                    "sha256": row["sha256"],
                    "issuing_authority": issuer,
                    "authority_class": authority_class,
                    "rejection_code": "media_type_magic_mismatch",
                    "rejection_detail": (
                        "GovInfo Link Service HTML error bytes were captured "
                        "under a .pdf filename"
                    ),
                }
            )
            continue
        issuer, authority_class = REVIEWED_SOURCE_METADATA[filename]
        candidates.append(
            {
                "source_document_id": source_document_id,
                "manifest_position": row["manifest_position"],
                "locator": locator,
                "retrieved_at_utc": row["retrieved_at_utc"],
                "source_url": row["source_url"],
                "media_type": declared_media_type,
                "byte_size": row["byte_size"],
                "sha256": row["sha256"],
                "issuing_authority": issuer,
                "authority_class": authority_class,
            }
        )
    candidates.sort(
        key=lambda item: item["source_document_id"].encode("utf-8")
    )
    rejected.sort(key=lambda item: item["source_document_id"].encode("utf-8"))
    if (
        len(candidates) != EXPECTED_SOURCE_DOCUMENT_CANDIDATE_COUNT
        or len(rejected) != EXPECTED_REJECTED_SOURCE_DOCUMENT_COUNT
    ):
        raise ValueError("legal source acceptance/rejection census drift")
    manifest_identity = {
        "locator": _full_file_locator(CAPTURE_MANIFEST_FILENAME, manifest_raw),
        "row_count": len(manifest_rows),
        "declared_source_byte_size": sum(
            row["byte_size"] for row in manifest_rows
        ),
    }
    return manifest_identity, candidates, rejected


def source_document_candidates(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> list[dict[str, Any]]:
    """Return the reviewed §19 rows from authenticated staged bytes."""

    _, candidates, _ = _verified_capture(capture_root)
    return candidates


def rejected_source_documents(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> list[dict[str, Any]]:
    """Return the explicit capture rows rejected before manifest admission."""

    _, _, rejected = _verified_capture(capture_root)
    return rejected


def legal_rule_input_identity(raw: bytes) -> dict[str, str]:
    """Construct the exact four-field §19 identity for canonical registry bytes."""

    value = strict_json_loads(raw, TARGET_REGISTRY_SCHEMA_VERSION)
    registry = _exact_keys(
        value, REGISTRY_TOP_LEVEL_FIELDS, TARGET_REGISTRY_SCHEMA_VERSION
    )
    if (
        registry["schema_version"] != TARGET_REGISTRY_SCHEMA_VERSION
        or registry["artifact_id"] != TARGET_REGISTRY_SCHEMA_VERSION
        or registry["artifact_vintage_id"]
        != TARGET_REGISTRY_ARTIFACT_VINTAGE_ID
    ):
        raise ValueError("historical legal registry identity literals drift")
    return {
        "path": TARGET_REGISTRY_PATH,
        "artifact_vintage_id": TARGET_REGISTRY_ARTIFACT_VINTAGE_ID,
        "schema_version": TARGET_REGISTRY_SCHEMA_VERSION,
        "sha256": _sha256(raw),
    }


def _source_authority_class_census(
    candidates: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    counts = Counter(row["authority_class"] for row in candidates)
    return [
        {
            "authority_class": authority_class,
            "authority_rank": AUTHORITY_RANK_BY_CLASS[authority_class],
            "source_document_count": counts[authority_class],
            "status": (
                "candidate_manifest_rows_verified"
                if counts[authority_class]
                else "no_candidate_source_document"
            ),
        }
        for authority_class in AUTHORITY_CLASSES
    ]


def _content_sha256(value: Mapping[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage["integrity"]["content_sha256"] = "0" * 64
    return _sha256(canonical_json_bytes(preimage))


def _dependency_rows() -> list[dict[str, Any]]:
    rows = copy.deepcopy(list(DEPENDENCY_ROWS))
    for row in rows:
        if (ROOT / row["required_path"]).exists():
            raise ValueError(
                f"registration-required dependency now exists: {row['dependency_id']}"
            )
    return rows


def _assemble_registration_required_audit(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    if (ROOT / TARGET_REGISTRY_PATH).exists():
        raise ValueError(
            "target historical legal registry unexpectedly exists"
        )
    design = verify_design_binding()
    manifest_identity, candidates, rejected = _verified_capture(capture_root)
    dependencies = _dependency_rows()
    gaps = copy.deepcopy(list(SOURCE_GAP_ROWS))
    constraints = copy.deepcopy(list(EVIDENCE_CONSTRAINT_ROWS))
    source_census = _source_authority_class_census(candidates)
    rule_census = copy.deepcopy(list(RULE_REGISTRY_CENSUS_ROWS))
    ordered_source_document_ids = [
        row["source_document_id"] for row in candidates
    ]
    value: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "design_binding": design,
        "staging": copy.deepcopy(STAGING_IDENTITY),
        "target_registry": {
            "path": TARGET_REGISTRY_PATH,
            "artifact_vintage_id": TARGET_REGISTRY_ARTIFACT_VINTAGE_ID,
            "schema_version": TARGET_REGISTRY_SCHEMA_VERSION,
            "status": "not_emitted_registration_required",
        },
        "capture_manifest_identity": manifest_identity,
        "source_document_candidates": candidates,
        "ordered_source_document_ids": ordered_source_document_ids,
        "source_document_candidate_count": len(candidates),
        "source_document_keyset_sha256": _sha256(
            canonical_json_bytes(ordered_source_document_ids)
        ),
        "source_document_rows_sha256": _sha256(
            canonical_json_bytes(candidates)
        ),
        "rejected_source_documents": rejected,
        "rejected_source_document_count": len(rejected),
        "rejected_source_document_rows_sha256": _sha256(
            canonical_json_bytes(rejected)
        ),
        "dependency_rows": dependencies,
        "dependency_count": len(dependencies),
        "dependency_sha256": _sha256(canonical_json_bytes(dependencies)),
        "source_gap_rows": gaps,
        "source_gap_count": len(gaps),
        "source_gap_sha256": _sha256(canonical_json_bytes(gaps)),
        "evidence_constraint_rows": constraints,
        "evidence_constraint_count": len(constraints),
        "evidence_constraint_sha256": _sha256(
            canonical_json_bytes(constraints)
        ),
        "source_authority_class_census": source_census,
        "source_authority_class_census_count": len(source_census),
        "source_authority_class_census_sha256": _sha256(
            canonical_json_bytes(source_census)
        ),
        "rule_registry_census": rule_census,
        "rule_registry_census_count": len(rule_census),
        "rule_registry_census_sha256": _sha256(
            canonical_json_bytes(rule_census)
        ),
        "registry_emitted": False,
        "failure_disposition": FAILURE_DISPOSITION,
        "status": "registration_required",
        "integrity": {
            "canonicalization": CANONICALIZATION,
            "content_sha256": "0" * 64,
            "structural_status": "pass",
            "source_byte_verification_status": (
                "pass_with_one_explicit_magic_rejection"
            ),
        },
    }
    value["integrity"]["content_sha256"] = _content_sha256(value)
    return value


def build_registration_required_audit(
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> dict[str, Any]:
    """Reconstruct the deterministic audit from authenticated staged bytes."""

    value = _assemble_registration_required_audit(capture_root)
    validate_registration_required_audit_structure(value)
    return value


def build_registry(capture_root: Path = DEFAULT_CAPTURE_ROOT) -> NoReturn:
    """Fail closed until every ratified inventory and rank-1 gap is closed."""

    audit = build_registration_required_audit(capture_root)
    raise RegistrationRequiredError(
        [row["dependency_id"] for row in audit["dependency_rows"]],
        [row["gap_id"] for row in audit["source_gap_rows"]],
        [row["constraint_id"] for row in audit["evidence_constraint_rows"]],
    )


def _validate_full_file_locator(
    value: object,
    *,
    filename: str,
    size_bytes: int,
    sha256: str,
    label: str,
) -> Mapping[str, Any]:
    locator = _exact_keys(
        value,
        (
            "location_type",
            "filename",
            "full_file_sha256",
            "size_bytes",
            "byte_start",
            "byte_end",
            "range_sha256",
        ),
        label,
    )
    if locator != {
        "location_type": "full_file_byte_range",
        "filename": filename,
        "full_file_sha256": sha256,
        "size_bytes": size_bytes,
        "byte_start": 0,
        "byte_end": size_bytes,
        "range_sha256": sha256,
    }:
        raise ValueError(f"{label} identity drift")
    for field in ("size_bytes", "byte_start", "byte_end"):
        _json_int(
            locator[field],
            f"{label}/{field}",
            positive=field != "byte_start",
        )
    return locator


def _validate_source_document_rows(
    rows: object, ordered_ids: object
) -> list[Mapping[str, Any]]:
    if (
        type(rows) is not list
        or len(rows) != EXPECTED_SOURCE_DOCUMENT_CANDIDATE_COUNT
    ):
        raise ValueError("source-document candidate domain drift")
    if type(ordered_ids) is not list:
        raise ValueError("ordered source-document IDs must be an array")
    checked: list[Mapping[str, Any]] = []
    for position, raw_row in enumerate(rows):
        row = _exact_keys(
            raw_row,
            SOURCE_DOCUMENT_FIELDS,
            f"source_document_candidates/{position}",
        )
        for field in SOURCE_DOCUMENT_FIELDS:
            if field not in {"manifest_position", "locator", "byte_size"}:
                _nonempty_string(row[field], f"source row {position}/{field}")
        _json_int(
            row["manifest_position"],
            f"source row {position}/manifest_position",
            positive=True,
        )
        _json_int(
            row["byte_size"], f"source row {position}/byte_size", positive=True
        )
        sha256 = row["sha256"]
        if _HEX64.fullmatch(sha256) is None:
            raise ValueError(f"source row {position} SHA-256 grammar drift")
        if row["source_document_id"] != f"legal-source:{sha256}":
            raise ValueError(f"source row {position} ID derivation drift")
        locator = _exact_keys(
            row["locator"],
            (
                "location_type",
                "filename",
                "full_file_sha256",
                "size_bytes",
                "byte_start",
                "byte_end",
                "range_sha256",
            ),
            f"source row {position}/locator",
        )
        filename = locator["filename"]
        if filename not in REVIEWED_SOURCE_METADATA:
            raise ValueError(f"source row {position} is not reviewed")
        _validate_full_file_locator(
            locator,
            filename=filename,
            size_bytes=row["byte_size"],
            sha256=sha256,
            label=f"source row {position}/locator",
        )
        issuer, authority_class = REVIEWED_SOURCE_METADATA[filename]
        if (
            row["issuing_authority"] != issuer
            or row["authority_class"] != authority_class
            or row["media_type"] != _declared_media_type(filename)
            or _RFC3339_SECONDS_UTC.fullmatch(row["retrieved_at_utc"]) is None
            or not row["source_url"].startswith("https://")
        ):
            raise ValueError(f"source row {position} reviewed metadata drift")
        checked.append(row)
    ids = [row["source_document_id"] for row in checked]
    expected_order = sorted(ids, key=lambda item: item.encode("utf-8"))
    if (
        ids != expected_order
        or len(ids) != len(set(ids))
        or ordered_ids != ids
    ):
        raise ValueError("source-document canonical key order drift")
    return checked


def _validate_rejected_source_rows(rows: object) -> list[Mapping[str, Any]]:
    if (
        type(rows) is not list
        or len(rows) != EXPECTED_REJECTED_SOURCE_DOCUMENT_COUNT
    ):
        raise ValueError("rejected source-document domain drift")
    checked: list[Mapping[str, Any]] = []
    for position, raw_row in enumerate(rows):
        row = _exact_keys(
            raw_row,
            REJECTED_SOURCE_DOCUMENT_FIELDS,
            f"rejected_source_documents/{position}",
        )
        for field in REJECTED_SOURCE_DOCUMENT_FIELDS:
            if field not in {"manifest_position", "locator", "byte_size"}:
                _nonempty_string(
                    row[field], f"rejected row {position}/{field}"
                )
        _json_int(
            row["manifest_position"],
            f"rejected row {position}/manifest_position",
            positive=True,
        )
        _json_int(
            row["byte_size"],
            f"rejected row {position}/byte_size",
            positive=True,
        )
        sha256 = row["sha256"]
        if _HEX64.fullmatch(sha256) is None or row["source_document_id"] != (
            f"legal-source:{sha256}"
        ):
            raise ValueError("rejected source identity drift")
        _validate_full_file_locator(
            row["locator"],
            filename=REJECTED_CAPTURE_FILENAME,
            size_bytes=row["byte_size"],
            sha256=sha256,
            label=f"rejected row {position}/locator",
        )
        issuer, authority_class = REJECTED_SOURCE_METADATA[
            REJECTED_CAPTURE_FILENAME
        ]
        if (
            row["declared_media_type"] != "application/pdf"
            or row["observed_media_type"] != "text/html"
            or row["issuing_authority"] != issuer
            or row["authority_class"] != authority_class
            or row["rejection_code"] != "media_type_magic_mismatch"
            or row["rejection_detail"]
            != "GovInfo Link Service HTML error bytes were captured under a .pdf filename"
            or _RFC3339_SECONDS_UTC.fullmatch(row["retrieved_at_utc"]) is None
            or not row["source_url"].startswith("https://")
        ):
            raise ValueError("reviewed rejected-source row drift")
        checked.append(row)
    return checked


def validate_registration_required_audit_structure(
    value: Mapping[str, Any],
) -> None:
    """Validate every closed schema and self-contained audit equation."""

    expected_top_level_fields = (
        "schema_version",
        "artifact_id",
        "design_binding",
        "staging",
        "target_registry",
        "capture_manifest_identity",
        "source_document_candidates",
        "ordered_source_document_ids",
        "source_document_candidate_count",
        "source_document_keyset_sha256",
        "source_document_rows_sha256",
        "rejected_source_documents",
        "rejected_source_document_count",
        "rejected_source_document_rows_sha256",
        "dependency_rows",
        "dependency_count",
        "dependency_sha256",
        "source_gap_rows",
        "source_gap_count",
        "source_gap_sha256",
        "evidence_constraint_rows",
        "evidence_constraint_count",
        "evidence_constraint_sha256",
        "source_authority_class_census",
        "source_authority_class_census_count",
        "source_authority_class_census_sha256",
        "rule_registry_census",
        "rule_registry_census_count",
        "rule_registry_census_sha256",
        "registry_emitted",
        "failure_disposition",
        "status",
        "integrity",
    )
    audit = _exact_keys(value, expected_top_level_fields, "audit")
    if (
        audit["schema_version"] != SCHEMA_VERSION
        or audit["artifact_id"] != ARTIFACT_ID
    ):
        raise ValueError("audit identity drift")
    if (
        type(audit["schema_version"]) is not str
        or type(audit["artifact_id"]) is not str
    ):
        raise ValueError("audit identity types drift")
    if audit["design_binding"] != {
        "path": DESIGN_PATH,
        "ratification_commit": DESIGN_RATIFICATION_COMMIT,
        "revision": DESIGN_REVISION,
        "blob_sha256": DESIGN_BLOB_SHA256,
    }:
        raise ValueError("audit design binding drift")
    design_binding = _exact_keys(
        audit["design_binding"],
        ("path", "ratification_commit", "revision", "blob_sha256"),
        "design_binding",
    )
    if type(design_binding["revision"]) is not int:
        raise ValueError("design revision must be a JSON integer")
    if audit["staging"] != STAGING_IDENTITY:
        raise ValueError("audit staging law drift")
    staging = _exact_keys(
        audit["staging"],
        (
            "staging_root_id",
            "relative_capture_path",
            "absolute_paths_serialized",
            "repo_authority_locator_id",
        ),
        "staging",
    )
    if staging["absolute_paths_serialized"] is not False:
        raise ValueError("audit staging path disposition drift")
    if audit["target_registry"] != {
        "path": TARGET_REGISTRY_PATH,
        "artifact_vintage_id": TARGET_REGISTRY_ARTIFACT_VINTAGE_ID,
        "schema_version": TARGET_REGISTRY_SCHEMA_VERSION,
        "status": "not_emitted_registration_required",
    }:
        raise ValueError("target registry disposition drift")

    manifest_identity = _exact_keys(
        audit["capture_manifest_identity"],
        (
            "locator",
            "row_count",
            "declared_source_byte_size",
        ),
        "capture_manifest_identity",
    )
    _validate_full_file_locator(
        manifest_identity["locator"],
        filename=CAPTURE_MANIFEST_FILENAME,
        size_bytes=EXPECTED_CAPTURE_MANIFEST_SIZE,
        sha256=EXPECTED_CAPTURE_MANIFEST_SHA256,
        label="capture_manifest_identity/locator",
    )
    if (
        manifest_identity["row_count"] != EXPECTED_CAPTURE_ROW_COUNT
        or manifest_identity["declared_source_byte_size"]
        != EXPECTED_DECLARED_SOURCE_BYTE_SIZE
    ):
        raise ValueError("capture manifest identity drift")
    for field in ("row_count", "declared_source_byte_size"):
        _json_int(
            manifest_identity[field],
            f"capture_manifest_identity/{field}",
            positive=True,
        )

    candidates = _validate_source_document_rows(
        audit["source_document_candidates"],
        audit["ordered_source_document_ids"],
    )
    rejected = _validate_rejected_source_rows(
        audit["rejected_source_documents"]
    )
    manifest_positions = [
        row["manifest_position"] for row in [*candidates, *rejected]
    ]
    if (
        audit["source_document_candidate_count"] != len(candidates)
        or type(audit["source_document_candidate_count"]) is not int
        or audit["source_document_keyset_sha256"]
        != _sha256(canonical_json_bytes(audit["ordered_source_document_ids"]))
        or audit["source_document_rows_sha256"]
        != _sha256(canonical_json_bytes(audit["source_document_candidates"]))
        or audit["rejected_source_document_count"] != len(rejected)
        or type(audit["rejected_source_document_count"]) is not int
        or audit["rejected_source_document_rows_sha256"]
        != _sha256(canonical_json_bytes(audit["rejected_source_documents"]))
        or sorted(manifest_positions)
        != list(range(1, EXPECTED_CAPTURE_ROW_COUNT + 1))
    ):
        raise ValueError("source-document count or digest drift")

    if type(audit["dependency_rows"]) is not list:
        raise ValueError("registration dependency rows must be an array")
    for position, raw_row in enumerate(audit["dependency_rows"]):
        row = _exact_keys(
            raw_row,
            (
                "dependency_id",
                "required_path",
                "required_artifact_id",
                "required_schema_version",
                "observed_status",
                "required_for",
                "failure_code",
            ),
            f"dependency_rows/{position}",
        )
        for field in (
            "dependency_id",
            "required_path",
            "required_artifact_id",
            "required_schema_version",
            "observed_status",
            "failure_code",
        ):
            _nonempty_string(row[field], f"dependency row {position}/{field}")
        if type(row["required_for"]) is not list or not row["required_for"]:
            raise ValueError("dependency required_for must be nonempty")
        for item in row["required_for"]:
            _nonempty_string(item, "dependency required_for item")
    if audit["dependency_rows"] != list(DEPENDENCY_ROWS):
        raise ValueError("registration dependency rows drift")
    if type(audit["source_gap_rows"]) is not list:
        raise ValueError("legal source gap rows must be an array")
    for position, raw_row in enumerate(audit["source_gap_rows"]):
        row = _exact_keys(
            raw_row,
            (
                "gap_id",
                "claim_id",
                "status_family",
                "authority_rank",
                "status",
                "missing_authority",
                "consequence",
            ),
            f"source_gap_rows/{position}",
        )
        for field in (
            "gap_id",
            "claim_id",
            "status_family",
            "status",
            "missing_authority",
            "consequence",
        ):
            _nonempty_string(row[field], f"source gap row {position}/{field}")
        _json_int(
            row["authority_rank"],
            f"source gap row {position}/authority_rank",
            positive=True,
        )
    if audit["source_gap_rows"] != list(SOURCE_GAP_ROWS):
        raise ValueError("legal source gap rows drift")
    if type(audit["evidence_constraint_rows"]) is not list:
        raise ValueError("legal evidence constraint rows must be an array")
    for position, raw_row in enumerate(audit["evidence_constraint_rows"]):
        row = _exact_keys(
            raw_row,
            (
                "constraint_id",
                "claim_id",
                "status_family",
                "authority_rank",
                "status",
                "evidence_finding",
                "required_resolution",
                "consequence",
            ),
            f"evidence_constraint_rows/{position}",
        )
        for field in (
            "constraint_id",
            "claim_id",
            "status_family",
            "status",
            "evidence_finding",
            "required_resolution",
            "consequence",
        ):
            _nonempty_string(
                row[field], f"evidence constraint row {position}/{field}"
            )
        _json_int(
            row["authority_rank"],
            f"evidence constraint row {position}/authority_rank",
            positive=True,
        )
    if audit["evidence_constraint_rows"] != list(EVIDENCE_CONSTRAINT_ROWS):
        raise ValueError("legal evidence constraint rows drift")
    if audit["rule_registry_census"] != list(RULE_REGISTRY_CENSUS_ROWS):
        raise ValueError("rule-registry census drift")
    exact_array_equations = (
        (
            "dependency_rows",
            "dependency_count",
            "dependency_sha256",
        ),
        ("source_gap_rows", "source_gap_count", "source_gap_sha256"),
        (
            "evidence_constraint_rows",
            "evidence_constraint_count",
            "evidence_constraint_sha256",
        ),
        (
            "source_authority_class_census",
            "source_authority_class_census_count",
            "source_authority_class_census_sha256",
        ),
        (
            "rule_registry_census",
            "rule_registry_census_count",
            "rule_registry_census_sha256",
        ),
    )
    for rows_field, count_field, digest_field in exact_array_equations:
        rows = audit[rows_field]
        if (
            type(rows) is not list
            or type(audit[count_field]) is not int
            or audit[count_field] != len(rows)
            or type(audit[digest_field]) is not str
            or _HEX64.fullmatch(audit[digest_field]) is None
            or audit[digest_field] != _sha256(canonical_json_bytes(rows))
        ):
            raise ValueError(f"{rows_field} count or digest drift")

    source_census = audit["source_authority_class_census"]
    if source_census != _source_authority_class_census(candidates):
        raise ValueError("source authority-class census drift")
    if sum(row["source_document_count"] for row in source_census) != len(
        candidates
    ):
        raise ValueError("source authority-class census total drift")
    for position, raw_row in enumerate(source_census):
        row = _exact_keys(
            raw_row,
            (
                "authority_class",
                "authority_rank",
                "source_document_count",
                "status",
            ),
            f"source_authority_class_census/{position}",
        )
        if (
            row["authority_class"] != AUTHORITY_CLASSES[position]
            or row["authority_rank"]
            != AUTHORITY_RANK_BY_CLASS[row["authority_class"]]
        ):
            raise ValueError("source authority-class census order drift")
        _json_int(row["source_document_count"], "source census count")

    for position, raw_row in enumerate(audit["rule_registry_census"]):
        row = _exact_keys(
            raw_row,
            (
                "claim_scope",
                "status_family_scope",
                "authority_rank",
                "authority_status",
                "rule_row_count",
            ),
            f"rule_registry_census/{position}",
        )
        if row["authority_rank"] is not None:
            _json_int(
                row["authority_rank"],
                "rule census authority rank",
                positive=True,
            )
        if (
            row["rule_row_count"] != 0
            or type(row["rule_row_count"]) is not int
        ):
            raise ValueError("unemitted registry has a nonzero rule census")

    if (
        audit["registry_emitted"] is not False
        or audit["failure_disposition"] != FAILURE_DISPOSITION
        or audit["status"] != "registration_required"
    ):
        raise ValueError("audit fail-closed disposition drift")
    integrity = _exact_keys(
        audit["integrity"],
        (
            "canonicalization",
            "content_sha256",
            "structural_status",
            "source_byte_verification_status",
        ),
        "integrity",
    )
    if (
        integrity["canonicalization"] != CANONICALIZATION
        or integrity["structural_status"] != "pass"
        or integrity["source_byte_verification_status"]
        != "pass_with_one_explicit_magic_rejection"
        or type(integrity["content_sha256"]) is not str
        or _HEX64.fullmatch(integrity["content_sha256"]) is None
        or integrity["content_sha256"] != _content_sha256(audit)
    ):
        raise ValueError("audit integrity drift")
    rendered = canonical_json_bytes(audit)
    if (
        b"/Users/" in rendered
        or b"~/" in rendered
        or b"maxghenis" in rendered
        or b"data/external/snapshots/" in rendered
    ):
        raise ValueError("audit serialized a host or repository-snapshot path")


def validate_registration_required_audit(
    value: Mapping[str, Any], capture_root: Path = DEFAULT_CAPTURE_ROOT
) -> None:
    """Validate structure and reproduce the audit from staged source bytes."""

    validate_registration_required_audit_structure(value)
    expected = _assemble_registration_required_audit(capture_root)
    if value != expected:
        raise ValueError("audit does not reproduce from staged source bytes")


def render_audit(capture_root: Path = DEFAULT_CAPTURE_ROOT) -> bytes:
    return canonical_json_bytes(
        build_registration_required_audit(capture_root)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT
    )
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_audit(args.capture_root)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != rendered:
            raise SystemExit(f"artifact drift: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
