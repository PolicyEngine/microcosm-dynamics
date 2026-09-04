"""An explicit dependency boundary for the optional graph example."""

import importlib
import sys

_GUIDANCE = (
    "The population graph needs Microcosm's typed model-artifact and keyed "
    "randomness interfaces. Install the reviewed microcosm-graph and "
    "microcosm-frame revisions together; see docs/population-graph.md. "
    "Legacy Dynamics does not require these packages."
)


def _python_version():
    return sys.version_info[:2]


def require_graph():
    """Refuse unsupported Python or a graph lacking the required interfaces."""
    if _python_version() < (3, 13):
        raise ImportError(
            "The optional population graph requires Python >=3.13."
        )
    try:
        decl = importlib.import_module("microcosm.graph.decl")
        kernel = importlib.import_module("microcosm.graph.kernel")
        randomness = importlib.import_module("microcosm.graph.randomness")
    except (ImportError, SyntaxError) as error:
        raise ImportError(_GUIDANCE) from error
    for name in ("ArtifactType", "ArtifactInput", "ArtifactOutput"):
        if not hasattr(decl, name):
            raise ImportError(_GUIDANCE)
    if not hasattr(kernel.SeedSource, "KEYED") or not hasattr(
        randomness, "keyed_uniform"
    ):
        raise ImportError(_GUIDANCE)
