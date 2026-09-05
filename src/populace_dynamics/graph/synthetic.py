"""Small hand-specified engineering inputs, independent of generated draws."""

from pathlib import Path

from .model import json_bytes


def write_synthetic_inputs(directory):
    """Write synthetic sources to an explicit directory; preserve edits."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    training = [
        {
            "person_id": 1001 + i,
            "event_year": 2013,
            "required_interview_year": 2013,
            "age_band": "0+",
            "sex": "female" if i < 4 else "male",
            "start_weight": 1.0,
            "exposure": 1.0,
            "death": float(i % 4 == 0),
        }
        for i in range(8)
    ]
    training.extend(
        [
            {**training[0], "person_id": 1009, "event_year": 2015},
            {
                **training[0],
                "person_id": 1010,
                "required_interview_year": 2015,
            },
        ]
    )
    rates = [
        {
            "lower_age": 0,
            "upper_age": 120,
            "age_band": "0+",
            "sex": sex,
            "central_rate": rate,
        }
        for sex, rate in (("female", 0.005), ("male", 0.006))
    ]
    initial = [
        {
            "person_id": 100 + i,
            "age": 30 + 2 * i,
            "sex": "female" if i % 2 == 0 else "male",
            "weight": float(1 + i % 3),
        }
        for i in range(20)
    ]
    holdout = {
        "scope": "synthetic_engineering",
        "fixture_max_abs_death_rate_gap": 0.25,
        "outcomes": [
            {
                "person_id": row["person_id"],
                "year": 2015,
                "age": row["age"] + 1,
                "death": int(i % 5 == 0),
            }
            for i, row in enumerate(initial)
        ],
    }
    result = {}
    for name, value in (
        ("training", training),
        ("rates", rates),
        ("initial", initial),
        ("holdout", holdout),
    ):
        path = directory / f"{name}.json"
        if not path.exists():
            path.write_bytes(json_bytes(value))
        result[name] = path
    return result
