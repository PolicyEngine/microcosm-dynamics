"""Assemble CE1 research fragments; verify source hashes before writing JSON.

Run with the clone's virtual-environment Python from the repository root.
The fragments retain the research work split; coverage_rules.json is the
single runtime input. This script fetches nothing.
"""

import json
from pathlib import Path

from populace_dynamics.income_resources.coverage_rules import (
    CAPTURE_DIRECTORY,
    SCHEMA_VERSION,
    CoverageRegistry,
)


def build(root: Path | None = None) -> str:
    """Validate fragments and return the complete canonical registry text."""
    root = Path(root) if root is not None else Path(__file__).resolve().parent

    def read(name):
        return json.loads((root / name).read_text())

    rules = []
    for name in (
        "government_rules.json",
        "se_rules.json",
        "other_rules.json",
        "se_modifier_rules.json",
    ):
        rules.extend(read(name))
    thresholds = []
    for name in (
        "thresholds_government.json",
        "thresholds_se.json",
        "thresholds_other.json",
    ):
        thresholds.extend(read(name))
    ret = read("earnings_test_root.json")
    ret["self_employment_guidance"] = read("earnings_test_se.json")
    ret["historical_research"] = read("ret_history_government.json")
    ret["definition_modifier_research"] = read("ret_history_modifiers.json")
    raw = {
        "schema_version": SCHEMA_VERSION,
        "income_years": [1968, 2026],
        "rules": rules,
        "thresholds": thresholds,
        "earnings_test": ret,
        "table_definitions": read("table_definitions_root.json"),
        "scope_status": "partial_statutory_registry_open_histories_refuse",
        "design": "docs/design/covered_earnings_v2.md",
        "rare_exclusion_ruling": "open_no_reading_selected",
        "open_questions": [
            {"rule_id": rule["rule_id"], "reason": rule["open_reason"]}
            for rule in sorted(rules, key=lambda row: row["rule_id"])
            if rule["open_reason"]
        ],
    }
    return CoverageRegistry.from_dict(
        raw, capture_root=CAPTURE_DIRECTORY
    ).to_json()


def main():
    root = Path(__file__).resolve().parent
    (root / "coverage_rules.json").write_text(build(), encoding="utf-8")


if __name__ == "__main__":
    main()
