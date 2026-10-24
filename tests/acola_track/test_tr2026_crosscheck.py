"""Cross-check only the registered December COLAs through the accessor."""

from decimal import Decimal

from populace_dynamics.acola_track.nulls import tr2026_inputs
from populace_dynamics.data import tr2026


def test_registered_cola_capture_matches_master_accessor():
    captured = tr2026_inputs()["cells"]
    entries = tr2026.cola_path(2027, 2029)
    assert tuple(entry.determination_year for entry in entries) == (
        2027,
        2028,
        2029,
    )
    for entry in entries:
        assert entry.effective_month == "December"
        assert entry.source == "tr2026_v_c1_projected"
        assert Decimal(str(entry.percent)) == Decimal(
            captured[str(entry.determination_year)]["percent"]
        )
