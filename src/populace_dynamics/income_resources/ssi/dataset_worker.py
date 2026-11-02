"""Public dataset route for explicit group links and independent cases.

Invariants: every person's explicit group links survive the public adapter;
inputs stay on their owners; case prefixes prevent shared IDs from joining
independent households; batched cases share year, policy, geography and
requested outputs; output rows follow caller person order; only requested
intermediates, SSI and original person IDs leave this worker. This module
imports no country-model internals and never saves a dataset.

Each entity has explicit weight 1.0 for the public adapter's auxiliary
bookkeeping. Federal SSI's inventoried formula closure reads no weights;
these records produce person benefits, not population aggregates. All SSI
contract inputs have already been resolved by the parent runner.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

_GROUP_ENTITIES = (
    "marital_unit",
    "tax_unit",
    "family",
    "spm_unit",
    "household",
)
_ID_KEYS = {
    "person_id",
    *(f"{entity}_id" for entity in _GROUP_ENTITIES),
    *(f"person_{entity}_id" for entity in _GROUP_ENTITIES),
}
_SHARED_FIELDS = ("year", "reform", "spm", "extra_variables")


def _prefix_ids(value: Any, prefix: str) -> Any:
    if isinstance(value, dict):
        remapped = {}
        for key, item in value.items():
            if key in _ID_KEYS:
                if not isinstance(item, str):
                    raise ValueError(f"Explicit {key} must be a string")
                remapped[key] = prefix + item
            else:
                remapped[key] = _prefix_ids(item, prefix)
        return remapped
    if isinstance(value, list):
        return [_prefix_ids(item, prefix) for item in value]
    if isinstance(value, tuple):
        return tuple(_prefix_ids(item, prefix) for item in value)
    return value


def calculate_dataset(case: Mapping[str, Any], pe: Any) -> dict[str, Any]:
    """Calculate an in-memory annual dataset through policyengine.py."""
    return calculate_dataset_batch([case], pe)[0]


def calculate_dataset_batch(
    cases: Sequence[Mapping[str, Any]], pe: Any
) -> list[dict[str, Any]]:
    """Calculate compatible independent households in one public run.

    Every original ID remains local to its case. Prefix all internal IDs,
    including group membership links, and restore original person IDs only
    after the combined simulation has completed. Different policies or
    periods cannot be pooled by this function.
    """
    from microdf import MicroDataFrame

    if not cases:
        return []
    first = cases[0]
    if any(
        case[field] != first[field]
        for case in cases[1:]
        for field in _SHARED_FIELDS
    ):
        raise ValueError("Dataset batch cases must share calculation settings")

    def table(entity: str, rows: list[dict[str, Any]]) -> MicroDataFrame:
        weight = f"{entity}_weight"
        return MicroDataFrame(
            [{**row, weight: 1.0} for row in rows], weights=weight
        )

    original_ids = [
        [links["person_id"] for links in case["person_links"]]
        for case in cases
    ]
    remapped_cases = [
        _prefix_ids(deepcopy(dict(case)), f"ssi0_case_{index}:")
        for index, case in enumerate(cases)
    ]
    settings = remapped_cases[0]
    internal_ids = [
        [links["person_id"] for links in case["person_links"]]
        for case in remapped_cases
    ]
    person_rows = []
    groups: dict[str, list[dict[str, Any]]] = {
        entity: [] for entity in _GROUP_ENTITIES
    }
    for case in remapped_cases:
        person_rows.extend(
            {**inputs, **links}
            for inputs, links in zip(
                case["people"], case["person_links"], strict=True
            )
        )
        groups["marital_unit"].extend(case["marital_unit_records"])
        groups["tax_unit"].extend(case["tax_unit_records"])
        for entity in ("family", "spm_unit", "household"):
            identity = f"{entity}_id"
            groups[entity].append({**case[entity], identity: case[identity]})
    data = pe.us.USYearData(
        person=table("person", person_rows),
        **{entity: table(entity, rows) for entity, rows in groups.items()},
    )
    dataset = pe.us.PolicyEngineUSDataset(
        name="SSI0 caller-supplied household",
        description="Explicit typed records; no population data loaded",
        year=settings["year"],
        data=data,
        filepath=None,
    )
    requested = list(dict.fromkeys(["ssi", *settings["extra_variables"]]))
    simulation = pe.Simulation(
        dataset=dataset,
        tax_benefit_model_version=pe.us.model,
        policy=settings["reform"],
        extra_variables={"person": requested},
        spm=settings["spm"],
    )
    # run() retains output in memory. ensure() or save() would persist it.
    simulation.run()
    person = simulation.output_dataset.data.person.set_index(
        "person_id", drop=False, verify_integrity=True
    )
    columns = list(dict.fromkeys(["person_id", *requested]))
    results = []
    for native_order, original_order in zip(
        internal_ids, original_ids, strict=True
    ):
        ordered = person.loc[native_order, columns].copy()
        ordered["person_id"] = original_order
        results.append({"person": ordered.to_dict(orient="records")})
    return results
