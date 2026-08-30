"""Generate docs/progress.md from docs/progress/progress.json.

The dashboard page is generated; edit the JSON and re-run this script.
Usage: python scripts/build_progress_page.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "progress" / "progress.json"
SCORECARD = ROOT / "docs" / "progress" / "scorecard.json"
DETAIL = ROOT / "docs" / "progress" / "detail.json"
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
        "Dynamics builds Social Security earnings histories from the "
        "PSID, and the corrected covered-earnings series is only as "
        "credible as the reading of the source documentation beneath "
        "it. Before that series ships, every piece of documentation "
        "the construction relies on is independently verified by the "
        "three arms below; the design is pre-registered and ratifies "
        "only when they complete. (Internally: the evidence campaign "
        f"behind {fw['amendment']}, under review in PR #{fw['pr']}, "
        f"{fw['pr_state']}; next step, the {fw['next_ceremony']}.)\n"
    )

    parts.append("## Already built\n")
    parts.append(
        "The foundations below are complete and in the repository "
        "today; the campaign tracked on this page is the verification "
        "layer on top of them.\n"
    )
    for f in data.get("foundations", []):
        parts.append(f"- [{f['text']}]({f['href']})")
    parts.append("")

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

    if DETAIL.exists():
        det = json.loads(DETAIL.read_text())
        parts.append("## Inside the numbers\n")
        parts.append(
            "The three drill-down tables below decompose each arm's "
            "progress bar row by row. Every row was extracted from the "
            "campaign's evidence archive and independently re-verified "
            "against the artifact named in its source column.\n"
        )

        pu = det["purpose"]
        parts.append("### Purpose census, document by document\n")
        parts.append(f"*What one unit is*: {pu['unit']}\n")
        parts.append(f"*Why the denominator is 20,815*: {pu['denominator']}\n")
        parts.append(
            "| Document | Ranks | Count | Status | Dispositions | "
            "Audit | Adopted |\n|---|---|---|---|---|---|---|"
        )
        for r in pu["rows"]:
            parts.append(
                f"| {r['document']} | R{r['rank_start']:,}–"
                f"R{r['rank_end']:,} | {r['ranks']:,} | {r['status']} "
                f"| {r.get('dispositions') or '—'} | "
                f"{r.get('audit') or '—'} | "
                f"{r.get('adopted_on') or '—'} |"
            )
        parts.append("")

        a3 = det["a3"]
        parts.append("### A3 classification, block by block\n")
        parts.append(f"*What one unit is*: {a3['unit']}\n")
        parts.append(
            "| Block | Final census | Audit | Status |\n|---|---|---|---|"
        )
        for r in a3["rows"]:
            parts.append(
                f"| {r['rank_start']:,}–{r['rank_end']:,} | "
                f"{r.get('final') or '—'} | {r.get('audit') or '—'} | "
                f"{r['status']} |"
            )
        parts.append("")

        q5 = det["q5"]
        parts.append("### Q5 annotation, sealed documents\n")
        parts.append(f"*What one unit is*: {q5['unit']}\n")
        parts.append(
            "| Document | Rows sealed | Verdict | Sealed |\n|---|---|---|---|"
        )
        for r in q5["rows"]:
            rs = r.get("rows_sealed")
            parts.append(
                f"| {r['label']} | {rs:,} | "
                f"{r.get('verdict') or '—'} | {r.get('sealed_on') or '—'} |"
                if rs is not None
                else f"| {r['label']} | — | {r.get('verdict') or '—'} | "
                f"{r.get('sealed_on') or '—'} |"
            )
        parts.append("")

    if SCORECARD.exists():
        sc = json.loads(SCORECARD.read_text())
        parts.append("## Development scorecard\n")
        parts.append(sc["headline"] + "\n")
        parts.append(
            "Every candidate model is registered before its single "
            "scored run, and every run — pass or fail — is committed. "
            "The failures are part of the record.\n"
        )
        parts.append(
            "| Gate | What it tests | Candidates | First pass |"
            "\n|---|---|---|---|"
        )
        for g in sc["gates"]:
            status = (
                g["first_pass"]
                if g["first_pass"]
                else (
                    "— (thresholds not yet locked)" if not g["locked"] else "—"
                )
            )
            parts.append(
                f"| **{g['name']}** | {g['tests']} | "
                f"{g['candidates'] or '—'} | {status} |"
            )
        parts.append("")

        ib = sc["incumbent_benchmarks"]
        parts.append("### Comparisons against the incumbent models\n")
        parts.append(ib["intro"] + "\n")
        for item in ib["items"]:
            link = f" ([source]({item['href']}))" if item["href"] else ""
            parts.append(
                f"- **{item['name']}** — *{item['status']}*. "
                f"{item['detail']}{link}"
            )
        parts.append("")

        cap = sc["capabilities"]
        parts.append("### Capability scorecard vs DYNASIM\n")
        parts.append(cap["intro"] + "\n")
        parts.append("| Component | DYNASIM | This project |\n|---|---|---|")
        for r in cap["rows"]:
            parts.append(
                f"| {r['component']} | {r['dynasim']} | {r['ours']} |"
            )
        parts.append("")

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
