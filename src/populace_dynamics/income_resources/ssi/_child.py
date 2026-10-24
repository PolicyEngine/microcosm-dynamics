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


def record_digest(record):
    """SHA-256 of a distribution's RECORD entries inside site-packages.

    Entries outside it (``../`` paths, such as console scripts) embed the
    interpreter's own path in their shebangs, so they differ between
    otherwise identical installations and are left out.
    """
    lines = [
        line
        for line in record.splitlines()
        if not line.lstrip('"').startswith("../")
    ]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def compatible_batch(cases):
    """Combine only cases whose policy and annual measurement are identical."""
    keys = ("year", "reform", "spm", "extra_variables")
    return len(cases) > 3 and all(
        case.get("person_links")
        and all(case[key] == cases[0][key] for key in keys)
        for case in cases
    )


def calculate_one(case, pe):
    """One case through its own public calculation path, or its error."""
    try:
        if case.get("backend") == "dataset":
            from dataset_worker import calculate_dataset

            return calculate_dataset(case, pe)
        arguments = {key: case[key] for key in HOUSEHOLD_ARGUMENTS}
        result = pe.us.calculate_household(**arguments)
        return {"person": result["person"]}
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"}


def calculate_cases(requests, pe):
    """Results in request order; no case's outcome depends on another's.

    A compatible batch is pooled into one calculation. If that calculation
    fails, the failure says only that some case failed, so every case is
    then calculated alone and only those that fail alone report an error.
    """
    if compatible_batch(requests):
        try:
            from dataset_worker import calculate_dataset_batch

            return calculate_dataset_batch(requests, pe)
        except Exception:
            pass
    return [calculate_one(case, pe) for case in requests]


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
        digest = record_digest(dist.read_text("RECORD") or "")
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

            cases = calculate_cases(job["cases"], pe)
    json.dump(
        {"versions": versions, "cases": cases}, sys.stdout, allow_nan=False
    )


if __name__ == "__main__":
    main()
