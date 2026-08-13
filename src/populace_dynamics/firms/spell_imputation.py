"""Phase-0 job-spell imputation — SIPP donors onto CPS persons (#192).

Workstream A's deliverable to workstream B: a CPS-wide person panel
carrying IC1 job spells. The persons are real ASEC respondents and the
donor spells are real SIPP job records; what is modelled is which
donor's *attributes* attach to which host person, using a quantile
regression forest (``microimpute``) exactly as the ECPS recipe does
for earnings histories.

**The firm-size x tenure bridge is named, not implicit.** ADR 0003
records that no current representative source observes firm size and
tenure jointly: ASEC ``FIRMSIZE`` refers to the preceding calendar
year's longest job, the biennial tenure supplement refers to the
current job and asks no firm-size question, SIPP 2014+ has tenure but
only *establishment* size, and NLSY has both for two
non-representative cohorts. The ratified bridge is therefore:

1. **primary** — the pre-redesign SIPP 2008 panel (2008-2013), the
   last representative panel observing worker-reported firm size at
   all locations alongside spells and tenure, its dated joint
   structure aged forward;
2. **proxy chain** — SIPP 2014+ establishment size x tenure mapped
   through the establishment-to-enterprise noise model implied by the
   IC2 semantics;
3. **caveat** — the ASEC reference-period mismatch is carried into the
   IC3 gate notes as a known label-misalignment term.

:class:`SpellImputationSpec` makes the choice an explicit argument. It
has no default: a run that does not say which bridge it used cannot be
refereed, and the two bridges give different joint structure.

**Imputing a band is not observing one.** The output is IC1-conforming
and feeds ``firms/assignment.py``, but a host person's imputed
``firm_size_band`` is a draw conditional on their observed
characteristics, not a measurement. Anything that treats it as
measured — a firm-size threshold count presented as a headcount rather
than an estimate — is over-reading the panel.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import ic1

__all__ = [
    "SpellImputationSpec",
    "BRIDGES",
    "DEFAULT_PREDICTORS",
    "IMPUTED_VARIABLES",
    "check_frames",
    "fit_spell_model",
    "impute_spells",
]

#: Ratified bridge identifiers (ADR 0003 conditioning DAG).
BRIDGES = ("sipp_2008_primary", "sipp_2014_proxy_chain")

#: Person characteristics conditioning the draw. They must be present
#: and comparably coded on *both* the donor and the host frame — a
#: predictor observed only on the donor cannot condition anything, and
#: silently dropping it changes the joint structure the bridge exists
#: to supply.
DEFAULT_PREDICTORS = (
    "age",
    "sex",
    "education",
    "industry_sector",
    "annual_earnings",
)

#: The spell attributes drawn from the donor.
IMPUTED_VARIABLES = ("firm_size_band_code", "tenure_months", "earnings_share")


@dataclass(frozen=True)
class SpellImputationSpec:
    """A registered imputation run.

    ``bridge`` and ``seed`` are required. The seed makes the draw
    reproducible, which the pre-registration discipline needs; the
    bridge records which joint firm-size x tenure structure was used,
    without which two runs are not comparable even at the same seed.
    """

    bridge: str
    seed: int
    predictors: tuple[str, ...] = DEFAULT_PREDICTORS
    imputed_variables: tuple[str, ...] = IMPUTED_VARIABLES
    #: Resolution of the inverse-CDF draw. The conditional
    #: distribution is evaluated on this many quantiles and each host
    #: person selects one; coarser grids quantise the draw.
    quantile_grid: int = 200

    def __post_init__(self) -> None:
        if self.bridge not in BRIDGES:
            raise ValueError(
                f"Unknown bridge {self.bridge!r}; ADR 0003 ratifies "
                f"{list(BRIDGES)}. A run must name its bridge: the two "
                "give different firm-size x tenure joint structure."
            )
        if not self.predictors:
            raise ValueError("At least one predictor is required.")


def check_frames(
    donor: pd.DataFrame, hosts: pd.DataFrame, spec: SpellImputationSpec
) -> None:
    """Check donor and host frames are compatible before fitting.

    Called by :func:`fit_spell_model` when ``hosts`` is supplied, and
    public so a caller can check compatibility before paying for a fit.
    """
    missing_donor = [c for c in spec.predictors if c not in donor.columns]
    missing_host = [c for c in spec.predictors if c not in hosts.columns]
    if missing_donor:
        raise ValueError(f"Donor frame lacks predictors {missing_donor}.")
    if missing_host:
        raise ValueError(
            f"Host frame lacks predictors {missing_host}. A predictor "
            "present only on the donor cannot condition the draw; dropping "
            "it silently would change the joint structure."
        )
    missing_targets = [
        c for c in spec.imputed_variables if c not in donor.columns
    ]
    if missing_targets:
        raise ValueError(
            f"Donor frame lacks imputed variables {missing_targets}."
        )
    leaked = [c for c in spec.imputed_variables if c in hosts.columns]
    if leaked:
        raise ValueError(
            f"Host frame already carries imputed variable(s) {leaked}. "
            "Imputing over an observed column would overwrite measurement "
            "with a draw; drop or rename the host column deliberately."
        )


def fit_spell_model(
    donor: pd.DataFrame,
    spec: SpellImputationSpec,
    *,
    weight_column: str | None = None,
    hosts: pd.DataFrame | None = None,
):
    """Fit the quantile regression forest on donor spells.

    ``donor`` is one row per donor job spell carrying the predictors
    and the imputed variables. ``weight_column`` passes the donor's
    survey weight through to ``microimpute``, which resamples on it —
    omitting it fits the model to the unweighted SIPP sample, which is
    not representative.
    """
    if hosts is not None:
        check_frames(donor, hosts, spec)
    else:
        missing = [c for c in spec.predictors if c not in donor.columns]
        if missing:
            raise ValueError(f"Donor frame lacks predictors {missing}.")
        missing = [c for c in spec.imputed_variables if c not in donor.columns]
        if missing:
            raise ValueError(f"Donor frame lacks imputed variables {missing}.")

    from microimpute.models import QRF

    model = QRF()
    return model.fit(
        X_train=donor,
        predictors=list(spec.predictors),
        imputed_variables=list(spec.imputed_variables),
        weight_col=weight_column,
    )


def impute_spells(
    fitted,
    hosts: pd.DataFrame,
    spec: SpellImputationSpec,
    *,
    person_id_column: str = "person_id",
    class_of_worker_column: str = "class_of_worker",
    band_codes: dict[int, str] | None = None,
) -> pd.DataFrame:
    """Draw spell attributes onto host persons and emit IC1 spells.

    ``class_of_worker`` is **carried from the host, never imputed**.
    It determines the calibration universe (ADR 0003) and whether a
    firm-size band is even defined, so drawing it from a donor would
    let the imputation decide which jobs the SUSB/QWI targets count.

    The returned frame conforms to IC1 and is validated before return,
    so a malformed draw fails here rather than downstream in the
    roster.
    """
    if person_id_column not in hosts.columns:
        raise ValueError(f"Host frame lacks {person_id_column!r}.")
    if class_of_worker_column not in hosts.columns:
        raise ValueError(
            f"Host frame lacks {class_of_worker_column!r}; class of worker "
            "is carried from the host, never imputed (ADR 0003)."
        )

    # Two target kinds need two different draws, and conflating them is
    # a silent-failure trap.
    #
    # A *categorical* target (the firm-size band) is not quantile-
    # addressable: microimpute returns the same modal class at every
    # quantile — measured, band code mean 1.505 at q=0.05 and at q=0.95
    # alike. Drawing it "at a quantile" therefore yields a deterministic
    # modal assignment: every host person in a predictor cell gets the
    # same band, the cross-sectional variance collapses to zero, and the
    # seed has no effect at all. That looks like a working imputation and
    # is not one. The correct draw samples each row from its predicted
    # class distribution, which ``return_probs=True`` exposes.
    #
    # A *continuous* target (tenure, earnings share) is quantile-
    # addressable, so it is drawn by inverse-CDF on a fixed grid.
    rng = np.random.default_rng(spec.seed)
    grid = np.round(np.linspace(0.005, 0.995, spec.quantile_grid), 4)
    predicted = fitted.predict(
        hosts[list(spec.predictors)], list(grid), return_probs=True
    )
    if not isinstance(predicted, dict):
        raise TypeError(
            "Expected microimpute predict() to return {quantile: frame}; "
            f"got {type(predicted)!r}. The per-row draw depends on that "
            "contract."
        )
    probabilities = predicted.pop("probabilities", {}) or {}
    frames = {
        float(q): pd.DataFrame(f).reset_index(drop=True)
        for q, f in predicted.items()
    }
    keys = np.array(sorted(frames))
    picks = np.searchsorted(keys, rng.random(len(hosts)), side="left").clip(
        0, len(keys) - 1
    )
    stacked = np.stack([frames[k].to_numpy() for k in keys])
    drawn = pd.DataFrame(
        stacked[picks, np.arange(len(hosts))],
        columns=frames[keys[0]].columns,
    )

    for name, payload in probabilities.items():
        if name not in drawn.columns:
            continue
        classes = np.asarray(payload["classes"])
        weights = np.asarray(payload["probabilities"], dtype=float)
        totals = weights.sum(axis=1, keepdims=True)
        if not np.isfinite(totals).all() or (totals <= 0).any():
            raise ValueError(
                f"Predicted class distribution for {name!r} is degenerate; "
                "cannot draw."
            )
        cumulative = np.cumsum(weights / totals, axis=1)
        uniforms = rng.random(len(drawn))[:, None]
        chosen = (uniforms > cumulative).sum(axis=1).clip(0, len(classes) - 1)
        drawn[name] = classes[chosen]

    codes = band_codes or {}
    bands = drawn.get("firm_size_band_code")
    if bands is None:
        raise ValueError("Imputation produced no firm_size_band_code column.")
    band_names = pd.Series(
        [codes.get(int(round(v))) for v in bands], dtype="object"
    )

    cow = hosts[class_of_worker_column].reset_index(drop=True)
    out = pd.DataFrame(
        {
            "person_id": hosts[person_id_column]
            .reset_index(drop=True)
            .astype("string"),
            "spell_id": 1,
            "start_period": hosts.get(
                "spell_start", pd.Series([pd.NaT] * len(hosts))
            ).reset_index(drop=True),
            "end_period": hosts.get(
                "spell_end", pd.Series([pd.NaT] * len(hosts))
            ).reset_index(drop=True),
            "industry": hosts["industry_sector"]
            .reset_index(drop=True)
            .astype("string"),
            "firm_size_band": band_names,
            "class_of_worker": cow,
            "earnings_share": pd.to_numeric(
                drawn.get("earnings_share"), errors="coerce"
            ).clip(0.0, 1.0),
            "primary_job": True,
        }
    )
    # Self-employed and unpaid-family spells have no defined band; the
    # draw does not get to invent one (ADR 0003).
    undefined = out["class_of_worker"].isin(ic1.NO_FIRM_SIZE_CLASSES)
    out.loc[undefined, "firm_size_band"] = pd.NA

    out = out[list(ic1.IC1_COLUMNS)]
    ic1.validate(out)
    out.attrs["bridge"] = spec.bridge
    out.attrs["seed"] = spec.seed
    out.attrs["predictors"] = list(spec.predictors)
    out.attrs["donor_observed"] = True
    out.attrs["band_is_imputed"] = True
    return out
