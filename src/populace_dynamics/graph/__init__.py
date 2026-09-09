"""Optional synthetic population-graph integration.

Importing this package does not import Microcosm or change legacy execution.
The graph entry point checks Python and the installed graph capabilities.
"""


def run_mortality_graph(**kwargs):
    """Run the existing mortality/ageing operations through Microcosm."""
    from ._compat import require_graph

    require_graph()
    from .runtime import run_mortality_graph as run

    return run(**kwargs)


__all__ = ["run_mortality_graph"]
