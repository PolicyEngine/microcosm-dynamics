"""Bridges from Microcosm Dynamics to external tax-benefit models.

:mod:`populace_dynamics.bridge.policyengine_us` passes Microcosm benefit
amounts to PolicyEngine-US as household inputs and decomposes the change
in PolicyEngine-US's ``household_net_income``.  The package is opt-in: the
historical projection never imports it, and it adds no dependency on
``policyengine-us`` (that model runs in a separate interpreter).
"""
