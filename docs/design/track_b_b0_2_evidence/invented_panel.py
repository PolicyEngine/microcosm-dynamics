"""An invented PSID-shaped panel for B0.2's disclosure calibration.

INVENTED DATA ONLY. Every value is drawn from a seeded generator, and no
PSID file, codebook or survey record is read. The panel has the shapes
B0.2's count script consumes (person-waves, family labor validity, the
2011 anchor and design fields) for 13 biennial waves, with attrition,
deaths, split-offs, missing ages (999), zero weights, nonsample sequence
numbers and invalid labor amounts. ``calibrate.py`` beside it uses it.
"""

import numpy as np
import pandas as pd

WAVES = tuple(range(1999, 2024, 2))
SENTINEL = 9_999_998


def invented_inputs(households=9000, seed=0, strata=80):
    rng = np.random.default_rng(seed)
    people = []
    labor = {w: [] for w in WAVES}
    next_person = 1
    next_household = 1
    live = (
        []
    )  # households: dict(id, members=[(pid, rel, birth)], stratum, cluster)

    def new_household(head_age, wave, spouse=True):
        nonlocal next_person, next_household
        birth = wave - head_age
        members = [(next_person, 10, birth)]
        next_person += 1
        if spouse:
            members.append((next_person, 20, birth + int(rng.integers(-6, 7))))
            next_person += 1
        for _ in range(int(rng.poisson(0.9 if head_age < 55 else 0.1))):
            members.append(
                (next_person, 30, birth + int(rng.integers(18, 40)))
            )
            next_person += 1
        household = {
            "id": next_household,
            "members": members,
            "stratum": int(rng.integers(1, strata + 1)),
            "cluster": int(rng.integers(1, 3)),
        }
        next_household += 1
        return household

    for _ in range(households):
        live.append(
            new_household(int(rng.integers(18, 95)), 1999, rng.random() < 0.55)
        )
    design = {}
    for wave in WAVES:
        survivors = []
        for household in live:
            if rng.random() < 0.035:  # attrition
                continue
            members = []
            for pid, rel, birth in household["members"]:
                age = wave - birth
                if rng.random() < (
                    0.002 if age < 60 else 0.02 + (age - 60) * 0.004
                ):
                    continue
                members.append((pid, rel, birth))
            if not members:
                continue
            if all(rel != 10 for _, rel, _ in members):
                pid, _, birth = members[0]
                members[0] = (pid, 10, birth)
            household["members"] = members
            survivors.append(household)
        for _ in range(int(households * 0.03)):  # split-offs and new entrants
            survivors.append(
                new_household(
                    int(rng.integers(18, 35)), wave, rng.random() < 0.4
                )
            )
        live = survivors
        for household in live:
            interview = wave * 100_000 + household["id"]
            for sequence, (pid, rel, birth) in enumerate(
                household["members"], 1
            ):
                age = wave - birth
                if rng.random() < 0.004:
                    age = 999
                weight = (
                    0.0
                    if rng.random() < 0.02
                    else float(rng.lognormal(0, 0.6))
                )
                present = sequence if rng.random() > 0.03 else 51
                people.append(
                    (pid, wave, age, min(present, 51), rel, weight, interview)
                )
                design.setdefault(
                    pid, (household["stratum"], household["cluster"])
                )
            labor[wave].append(
                {
                    "interview": interview,
                    "head_labor": (
                        float(SENTINEL) if rng.random() < 0.03 else 1.0
                    ),
                    "spouse_labor": (
                        float(SENTINEL) if rng.random() < 0.05 else 0.0
                    ),
                    "head_acc": int(rng.random() < 0.1),
                    "spouse_acc": int(rng.random() < 0.08),
                }
            )
    columns = [
        "person_id",
        "period",
        "age",
        "sequence",
        "relationship",
        "weight",
        "interview",
    ]
    person_wave = pd.DataFrame(people, columns=columns)
    labor = {w: pd.DataFrame(rows) for w, rows in labor.items()}
    anchor = (
        person_wave.loc[person_wave["period"] == 2011]
        .drop(columns="period")
        .copy()
    )
    anchor["weight"] = anchor["weight"] * rng.uniform(0.8, 1.2, len(anchor))
    design = pd.DataFrame(
        [(pid, s, c) for pid, (s, c) in design.items()],
        columns=["person_id", "stratum", "cluster"],
    )
    return person_wave, labor, anchor, design
