"""Keep the legacy registries and every registered consumer unchanged."""

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# origin/master at the assigned checkpoint, 75cd35245f1a0c12e7a23b048a7d126c74ad8ecb.
PINS = {
    "src/populace_dynamics/cola_track_a/config.py": "8c72a3164fc8b185f51f8f888b1f6678a801cd665929cdd0575fa10fb877dfae",
    "src/populace_dynamics/fra68_track/config.py": "2bb435e02025f5264991956935e5a33a1179d3b1d331de4b24bbe6c5e4bee141",
    "src/populace_dynamics/fra68_track/reform.py": "47a35589fbff9022b13bc37b388febf0788a2c3fc03a252cee1895b5d0187a29",
    "src/populace_dynamics/scenario_benefits.py": "dffe28fdac66eb849f387ed3a481b6aee85d470946951a755196761c70cc4cbf",
    "src/populace_dynamics/track_a_v2/matrix.py": "ffd878d257f35ce551db589411d81a52ac7f121a0648edaf57f69f7393a331e8",
    "src/populace_dynamics/track_a_v2/runner.py": "5df9d33b8a443cca2c31c5150ec930bc7b6862e3c4b28b19584fe1d596283cde",
    "scripts/track_a_dry_run.py": "2bb935dd9d7e2ac9dc194dcc41e050b91e3894d056c3076cb6e4414927d45a4a",
}


@pytest.mark.parametrize("path, digest", PINS.items())
def test_legacy_registries_constants_and_consumers_are_byte_unchanged(
    path, digest
):
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_the_legacy_matrix_and_registered_rate_check_still_work():
    import importlib.util

    from populace_dynamics.cola_track_a.runner import tr2008_baseline_cola
    from populace_dynamics.estimates.parameters import load_cola_history
    from populace_dynamics.track_a_v2.matrix import MATRIX

    assert len(MATRIX) == 68
    spec = importlib.util.spec_from_file_location(
        "acola_legacy_dry", ROOT / "scripts/track_a_dry_run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._spec_rate_check(tr2008_baseline_cola(load_cola_history()))
