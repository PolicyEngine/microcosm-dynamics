"""Structure-only inspection of cached Microcosm US frame files.

No outcome variable is summarized. For each file the script prints entity
row counts, the person column list, education-like column names,
``source_year`` and ``person_support_channel`` record counts, the weight
share by support channel, the age codes at 80 and over, and the Kish
effective sample size of persons from household weights. Written for the
microcosm-start plan, 2026-10-04.

Usage: ``python frame_structure.py <tag> <path> [<tag> <path> ...]``
"""

import collections
import sys

import h5py
import numpy as np

ENTITIES = (
    "person",
    "household",
    "tax_unit",
    "family",
    "spm_unit",
    "marital_unit",
)


def _decode(values):
    return np.array(
        [v.decode() if isinstance(v, bytes) else v for v in values]
    )


def inspect(tag: str, path: str) -> None:
    f = h5py.File(path, "r")
    person = f["person"]["table"]
    household = f["household"]["table"][:]
    indexed = set(f["person"]["_i_table"].keys())
    names = sorted((set(person.dtype.names or []) | indexed) - {"index"})
    print(f"===== {tag}")
    for entity in ENTITIES:
        print(f"  {entity} rows: {f[entity]['table'].shape[0]}")
    print(f"  person columns ({len(names)}): {', '.join(names)}")
    edu = [
        n
        for n in names
        if "HGA" in n or "educ" in n.lower() or "attain" in n.lower()
    ]
    print("  education-like columns:", edu)

    household_ids = person.fields(["person_household_id"])[:][
        "person_household_id"
    ]
    weight_by_household = dict(
        zip(
            household["household_id"],
            household["household_weight"],
            strict=True,
        )
    )
    w = np.array([weight_by_household[h] for h in household_ids])
    kish = w.sum() ** 2 / (w**2).sum()
    print(
        f"  kish_effective_n_persons: {kish:.1f}"
        f"  max household weight: {household['household_weight'].max():.1f}"
        f"  sum person weight (M): {w.sum() / 1e6:.1f}"
    )

    columns = person.dtype.names
    for column in ("source_year", "person_support_channel"):
        if column not in columns:
            continue
        values = _decode(person.fields([column])[:][column])
        counts = collections.Counter(values.tolist())
        print(f"  {column} record counts:", dict(counts))
        if column == "person_support_channel":
            for key in counts:
                share = w[values == key].sum() / w.sum()
                print(f"    weight share {key}: {share:.3f}")
    if "age" in columns:
        age = person.fields(["age"])[:]["age"]
        top = sorted(set(age[age >= 80].tolist()))
        print("  age max:", age.max(), " distinct ages >= 80:", top)


def main(argv: list[str]) -> None:
    pairs = argv[1:]
    if len(pairs) % 2:
        raise SystemExit("expected <tag> <path> pairs")
    for tag, path in zip(pairs[0::2], pairs[1::2], strict=True):
        inspect(tag, path)


if __name__ == "__main__":
    main(sys.argv)
