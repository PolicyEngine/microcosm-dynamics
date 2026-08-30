"""Generate docs/progress.md from docs/progress/progress.json.

The dashboard page is generated; edit the JSON and re-run this script.
Usage: python scripts/build_progress_page.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "progress" / "progress.json"
PAGE = ROOT / "docs" / "progress.md"

BAR_TEMPLATE = """
<div style="margin: 1.1em 0 1.4em 0;">
  <div style="display: flex; justify-content: space-between;
              align-items: baseline;">
    <strong>{label}</strong>
    <span style="font-variant-numeric: tabular-nums;">
      {done:,} / {total:,} &middot; {pct:.1f}%</span>
  </div>
  <div style="background: #e9ecef; border-radius: 6px; height: 14px;
              margin: 0.35em 0;">
    <div style="background: #2c6496; border-radius: 6px; height: 14px;
                width: {pct:.1f}%;"></div>
  </div>
  <div style="font-size: 0.9em; color: #555;">{unit}.
  {description}</div>
</div>
"""


def build() -> str:
    data = json.loads(DATA.read_text())
    parts: list[str] = []
    parts.append(
        "<!-- GENERATED FILE - DO NOT EDIT. Edit "
        "docs/progress/progress.json and run "
        "scripts/build_progress_page.py -->\n"
    )
    parts.append("# Development progress\n")
    parts.append(
        f"*Snapshot as of {data['as_of']} (UTC); updated at least "
        "daily while the evidence campaign is active. The data behind "
        "this page is committed at "
        "[`docs/progress/progress.json`](progress/progress.json).*\n"
    )
    fw = data["framework"]
    parts.append(
        "This page tracks the evidence campaign behind "
        f"{fw['amendment']}: three verification arms that must complete "
        "before the A4 evidence freeze and the ratification ceremony. "
        f"The design itself is under review in PR #{fw['pr']} "
        f"({fw['pr_state']}); the next ceremony step is the "
        f"{fw['next_ceremony']}.\n"
    )

    parts.append("## Verification arms\n")
    for arm in data["arms"]:
        pct = 100.0 * arm["done"] / arm["total"]
        parts.append(
            BAR_TEMPLATE.format(
                label=arm["label"],
                done=arm["done"],
                total=arm["total"],
                pct=pct,
                unit=arm["unit"],
                description=arm["description"],
            )
        )

    fc = data["forecast"]
    parts.append("## Timeline forecast\n")
    parts.append(
        f"From the pre-registered timeline ledger, entry "
        f"{fc['ledger_entry']} (registered {fc['registered_at']}). "
        "Dates are point-in-time forecasts, not commitments; the ledger "
        "records every revision with its reasons.\n"
    )
    parts.append("| Milestone | p50 | p80 |\n|---|---|---|")
    for m in fc["milestones"]:
        parts.append(f"| {m['name']} | {m['p50']} | {m['p80']} |")
    parts.append("")
    for m in fc["milestones"]:
        parts.append(f"- **{m['name'].split(' — ')[0]}**: {m['note']}")
    parts.append("")

    parts.append("## Recent milestones\n")
    for ms in data["milestones"]:
        parts.append(f"- **{ms['date']}** — {ms['text']}")
    parts.append("")

    parts.append("## How these numbers are produced\n")
    parts.append(
        "Every block of work moves through the same pipeline before it "
        "counts here: a full pass over the block, an independent dense "
        "audit, an adjudication step where audits disagree, and a "
        "correction sweep whose output is folded into the governing "
        "ledger. Q5 documents are annotated by two independent lanes "
        "and sealed only by a reconciliation of both. Nothing on this "
        "page is self-reported by the lane that produced it.\n"
    )

    parts.append("## Links\n")
    for ln in data["links"]:
        parts.append(f"- [{ln['text']}]({ln['href']})")
    parts.append("")

    return "\n".join(parts)


if __name__ == "__main__":
    PAGE.write_text(build())
    print(f"wrote {PAGE}")
