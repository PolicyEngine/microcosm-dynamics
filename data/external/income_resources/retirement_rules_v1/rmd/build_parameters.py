"""Extract both tables from pinned Federal Register plain-text renditions.

Keep owner ages 70--120 (72--120 from 2022) and spouse ages 0--120.
GovInfo's 2002 table prints a triangle; use its transposed entry only
where the requested entry is absent. The 115+ cells extend through 120.
The source's stray ``94`` after the 90--99 header is not a column.
Both renditions contain defects at young owner ages outside this API's
coverage; do not repair or encode those rows (see research_note.md).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def extract(vintage):
    text = (ROOT / f"tables{vintage}.html").read_text().replace("\x00", "")
    if vintage == "2003":
        start = text.index("                         Uniform Lifetime Table")
        end = text.index("    A-4.", start)
        text = text[start:end]
    else:
        start = text.index("    (c) Uniform Lifetime Table.")
        end = text.index("    (e)", start)
        text = text[start:end]
    uniform = {}
    joint = {}
    columns = None
    for line in text.splitlines():
        if "Ages" in line:
            numbers = [int(x) for x in re.findall(r"\d+", line)]
            columns = [numbers[0]]
            for n in numbers[1:]:
                if n != columns[-1] + 1:
                    break
                columns.append(n)
            continue
        match = re.match(r"^(\d+)(\+)?(?:\.+|\s{2,})(.*)$", line)
        if not match:
            continue
        age = int(match[1])
        values = [float(x) for x in re.findall(r"\d+\.\d+", match[3])]
        if not values:
            continue
        if columns is None:
            assert len(values) == 1, line
            uniform[age] = values[0]
        else:
            if vintage == "2022" and age == 19 and columns[0] == 27:
                assert len(values) == len(columns) - 1
                continue
            assert len(values) == len(columns), line
            for col, value in zip(columns, values, strict=True):
                joint[age, col] = value
    last = 115 if vintage == "2003" else 120
    minimum = 70 if vintage == "2003" else 72
    assert set(uniform) == set(range(minimum, last + 1))
    covered = {}
    for age in range(minimum, 121):
        for spouse in range(121):
            a, b = min(age, last), min(spouse, last)
            direct, transposed = joint.get((a, b)), joint.get((b, a))
            if direct is not None and transposed is not None:
                assert direct == transposed, (a, b, direct, transposed)
            value = direct if direct is not None else transposed
            assert value is not None and value >= 1
            covered[age, spouse] = value
    return {
        "uniform": {
            str(a): uniform[min(a, last)] for a in range(minimum, 121)
        },
        "joint": {
            str(a): {str(b): covered[a, b] for b in range(121)}
            for a in range(minimum, 121)
        },
    }


if __name__ == "__main__":
    tables = {
        "schema_version": 1,
        "disputed_historical_joint_cell": {
            "cfr_literal_60_3": 60.3,
            "irs_publication_63_0": 63.0,
        },
    } | {vintage: extract(vintage) for vintage in ("2003", "2022")}
    (ROOT / "parameters.json").write_text(json.dumps(tables, indent=2) + "\n")
    print("Validated covered owner/spouse cells and both Uniform tables")
