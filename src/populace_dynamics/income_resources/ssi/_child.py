"""JSON worker. Calculations use only policyengine.py's public API.

This script intentionally imports no project package in the isolated venv.
Version and file checks run before importing policyengine.
"""

import contextlib
import hashlib
import importlib.metadata as metadata
import io
import json
import sys

HOUSEHOLD_ARGUMENTS = (
    "people",
    "marital_unit",
    "tax_unit",
    "family",
    "spm_unit",
    "household",
    "year",
    "reform",
    "extra_variables",
    "spm",
)


def compatible_batch(cases):
    """Combine only cases whose policy and annual measurement are identical."""
    keys = ("year", "reform", "spm", "extra_variables")
    return len(cases) > 3 and all(
        case.get("person_links")
        and all(case[key] == cases[0][key] for key in keys)
        for case in cases
    )


def main():
    job = json.load(sys.stdin)
    pin = job["pin"]
    expected_versions = {
        **pin.get("environment_versions", {}),
        **pin["versions"],
    }
    actual_versions = {}
    errors = []
    for name, expected in expected_versions.items():
        try:
            actual_versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            actual_versions[name] = None
        if actual_versions[name] != expected:
            errors.append(
                f"{name}: installed {actual_versions[name]}, pinned {expected}"
            )
    versions = {name: actual_versions[name] for name in pin["versions"]}
    for name in pin["versions"]:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        record = dist.read_text("RECORD") or ""
        digest = hashlib.sha256(record.encode()).hexdigest()
        if digest != pin["record_sha256"][name]:
            errors.append(f"{name}: installation RECORD differs from pin")
            continue
    cases = []
    if errors:
        cases = [{"error": "; ".join(errors)} for _ in job["cases"]]
    else:
        # Country imports and incidental engine diagnostics cannot corrupt
        # the stdout protocol. No PE-US implementation is used by this code.
        with contextlib.redirect_stdout(io.StringIO()):
            import policyengine as pe

            requests = job["cases"]
            if compatible_batch(requests):
                try:
                    from dataset_worker import calculate_dataset_batch

                    cases = calculate_dataset_batch(requests, pe)
                except Exception as error:
                    cases = [
                        {"error": f"{type(error).__name__}: {error}"}
                        for _ in requests
                    ]
            else:
                for case in requests:
                    try:
                        if case.get("backend") == "dataset":
                            from dataset_worker import calculate_dataset

                            cases.append(calculate_dataset(case, pe))
                        else:
                            arguments = {
                                key: case[key] for key in HOUSEHOLD_ARGUMENTS
                            }
                            result = pe.us.calculate_household(**arguments)
                            cases.append({"person": result["person"]})
                    except Exception as error:
                        cases.append(
                            {"error": f"{type(error).__name__}: {error}"}
                        )
    json.dump(
        {"versions": versions, "cases": cases}, sys.stdout, allow_nan=False
    )


if __name__ == "__main__":
    main()
