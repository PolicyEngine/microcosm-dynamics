"""Name open-population refusals from ``docs/design/open_population.md`` §8.

The design was approved in ruling d1925. The marital compatibility refusal
enforces its §§5.4 and 7 requirement that emigration never causes widowhood.
"""


class OpenPopulationError(ValueError):
    """Refuse an unsupported or incoherent open-population run."""

    code = "OPEN_POPULATION_REFUSED"

    def __init__(self, message: str) -> None:
        super().__init__(f"{self.code}: {message}")


class AccountingIdentityError(OpenPopulationError):
    """Refuse a run whose declared flows do not conserve its stock."""

    code = "ACCOUNTING_IDENTITY_FAIL"


class IdOrStreamCollision(OpenPopulationError):
    """Refuse an unsafe ID namespace or an unregistered production horizon."""

    code = "ID_OR_STREAM_COLLISION"


class EmigrationMaritalIncompatibility(OpenPopulationError):
    """Refuse emigration when the marital adapter cannot separate exit causes."""

    code = "EMIGRATION_MARITAL_INCOMPATIBLE"


class GateTargetRefused(OpenPopulationError):
    """Refuse metadata outside the unaligned gate facade (design §5.1)."""


class ControlSourceUnavailable(OpenPopulationError):
    """Refuse a control or target the run cannot pin (design §8)."""

    code = "CONTROL_SOURCE_UNAVAILABLE"


class UniverseBridgeUnresolved(OpenPopulationError):
    """Refuse a control with no registered bridge to the roster (design §8)."""

    code = "UNIVERSE_BRIDGE_UNRESOLVED"


class TimingBridgeUnresolved(OpenPopulationError):
    """Refuse a schedule with no registered timing bridge (design §8)."""

    code = "TIMING_BRIDGE_UNRESOLVED"


class ExtrapolationUndeclared(OpenPopulationError):
    """Refuse a query outside fitted support with no rule (design §8)."""

    code = "EXTRAPOLATION_UNDECLARED"
