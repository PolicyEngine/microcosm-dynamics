"""Assemble CE1 research fragments; verify source hashes before writing JSON.

Run with the clone's virtual-environment Python from the repository root.
The fragments retain the research work split; coverage_rules.json is the
single runtime input. This script fetches nothing.
"""

import json
from pathlib import Path

from populace_dynamics.income_resources.coverage_rules import CoverageRegistry


def main():
    root = Path(__file__).resolve().parent

    def read(name):
        return json.loads((root / name).read_text())

    rules = []
    for name in ("government_rules.json", "se_rules.json", "other_rules.json"):
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
    if (root / "ret_history_government.json").exists():
        ret["historical_research"] = read("ret_history_government.json")
    raw = {
        "schema_version": "coverage_rules.ce1.v1",
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
    registry = CoverageRegistry.from_dict(raw, capture_root=root)
    (root / "coverage_rules.json").write_text(registry.to_json())
    print(
        f"Verified {len(registry.rules)} rules, "
        f"{len(registry.families)} families, "
        f"{len(registry.thresholds)} thresholds."
    )


if __name__ == "__main__":
    main()
