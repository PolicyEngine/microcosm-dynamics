"""Staged setup metadata and invented records only; no data files are opened.

The POPULACE_DYNAMICS_PSID_DIR override locates metadata; an absent setup
skips its wave cleanly. Codebooks supplied the registry's page locators,
but these integration tests read setup files only.
"""

import hashlib
import os
from io import StringIO
from pathlib import Path

import pytest

from populace_dynamics.data import psid
from populace_dynamics.data import psid_income_wealth as reader
from tests.income_resources.test_psid_income_wealth import invented_value


def staged_setup(wave):
    root = Path(
        os.environ.get(
            "POPULACE_DYNAMICS_PSID_DIR", "~/PolicyEngine/psid-data"
        )
    ).expanduser()
    registry = reader.wave_registry(wave)
    path = root / registry["setup"]["relative_path"]
    if not path.is_file():
        pytest.skip(f"PSID {wave} setup metadata is not staged")
    return root, path


@pytest.mark.parametrize("wave", reader.INCOME_WAVES)
def test_each_registered_label_column_and_pin_matches_staged_setup(wave):
    root, path = staged_setup(wave)
    reader.verify_setup(wave, path)
    for pin in reader.wave_registry(wave).get("setup_pins", []):
        companion = root / pin["relative_path"]
        assert companion.suffix.lower() in (".sps", ".sas", ".do")
        if not companion.is_file():
            pytest.skip("Companion setup metadata is not staged")
        assert (
            hashlib.sha256(companion.read_bytes()).hexdigest() == pin["sha256"]
        )


@pytest.mark.parametrize(
    ("wave", "kind"),
    [
        *((w, "income") for w in reader.INCOME_WAVES),
        *((w, "wealth") for w in reader.WEALTH_WAVES),
    ],
)
def test_invented_records_follow_staged_column_specifications(wave, kind):
    _, path = staged_setup(wave)
    layout = psid.parse_sps_layout(path)
    positions = layout.set_index("name")
    registry = reader.wave_registry(wave)
    items = registry[kind]
    if kind == "wealth":
        items = {"interview": registry["income"]["interview"], **items}
    overrides = (
        {"head_labor": 87654, "head_age": 999, "wife_age": 0}
        if kind == "income"
        else {"wealth1": -87654, "wealth2": -86543, "home_equity": 1111}
    )
    records = []
    for interview in (37, 2, 91):
        record = [" "] * int(layout["end"].max())
        for concept, item in items.items():
            position = positions.loc[item["variable"]]
            start, end = int(position["start"]), int(position["end"])
            value = (
                interview
                if concept == "interview"
                else overrides.get(concept, invented_value(concept, item))
            )
            token = f'{value:.{item.get("decimals", 0)}f}'
            assert len(token) <= end - start + 1
            record[start - 1 : end] = token.rjust(end - start + 1)
        records.append("".join(record))
    function = getattr(reader, f"read_family_{kind}")
    result = function(
        wave, setup_path=path, records_path=StringIO("\n".join(records) + "\n")
    )
    assert result["interview"].tolist() == [37, 2, 91]
    if kind == "income":
        assert result["head_labor"].tolist() == [87654] * 3
        assert result["head_age"].isna().all()
        assert result["wife_age"].isna().all()
        assert not result["wife_present"].any()
    else:
        assert result["wealth1"].tolist() == [-87654] * 3
