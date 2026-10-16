"""Protect aggregate projection diagnostics against cross-result differencing.

Verification class: labelled diagnostic under ruling d1408. Admitted scope:
publication of the retained COLA/FRA delayed-credit-window diagnostic only
(42 USC 402(w)(2)(A)). This pure helper reads no file and computes no payment.
Private membership ledgers stay with the caller and are never returned.
"""

from __future__ import annotations

MARKER = "suppressed_complementary"
SUPPORTS = ("supported", "unsupported_pre1917")


def _small_difference(left, right):
    return 0 < len(left - right) < 10 or 0 < len(right - left) < 10


def _event_sets(records, *, recipient):
    people = {record[1] for record in records}
    workers = {
        (record[2], "old_age") if recipient else (record[1], record[2])
        for record in records
    }
    return people, workers


def _released(cell, key="people"):
    count = cell.get(key)
    return (
        isinstance(count, (int, float))
        and not isinstance(count, bool)
        and count >= 10
    )


def _wave_groups(ledger, result):
    groups = {}
    for (support, role), records in ledger["events"].items():
        for wave in {record[0] for record in records}:
            cell = (
                result.get("counts", {})
                .get(str(wave), {})
                .get(f"{support}/{role}", {})
            )
            if not _released(cell):
                continue
            selected = {record for record in records if record[0] == wave}
            groups[(wave, support, role)] = _event_sets(
                selected,
                recipient=role == "recipient" or role.endswith("_recipient"),
            )
    return groups


def _row_sets(ledger, row, support, role):
    events = ledger["row_events"]
    records = events.get((row, support, role), set())
    associations = events.get((row, support, "recipient"), set())
    links = events.get((row, support, f"{role}_recipient"), set())
    if not links:
        links = {
            (wave, recipient, worker)
            for wave, recipient, worker in associations
            if (wave, worker, "old_age") in records
        }
    admitted = ledger["admitted_people_by_row"].get(row, set())
    people = {recipient for _, recipient, _ in links if recipient in admitted}
    workers = {
        (worker, "old_age")
        for _, recipient, worker in links
        if recipient in people
    }
    if role == "positive_opening_stock_adjustment":
        workers.update(
            (record[1], "old_age")
            for record in records
            if record[1] in admitted
        )
        people.update(worker for worker, _ in workers)
    return people, workers


def _flag_cells(result, *, released_only=False):
    for row, values in result.get(
        "admitted_beneficiary_counts_by_row", {}
    ).items():
        for name, cell in values.items():
            if (
                "/" in name
                and isinstance(cell, dict)
                and (not released_only or _released(cell))
            ):
                support, role = name.split("/", 1)
                yield row, support, role, cell


def _mask_flag_cell(cell):
    """Mask a positive cell together; preserve empty cells and existing <10."""
    people = cell.get("people")
    if not isinstance(people, (int, float)) or people <= 0:
        return False
    for key, value in cell.items():
        count = key in ("people", "worker_people", "worker_records")
        money = any(word in key for word in ("weight", "share"))
        description = key.endswith(("_definition", "_denominator", "_reason"))
        if (count or money) and not description and value is not None:
            if value != "<10":
                cell[key] = MARKER
    return True


def _mask_changes(cell):
    masked = False
    count = cell.get("changed_recipients")
    if isinstance(count, (int, float)) and count > 0:
        cell["changed_recipients"] = MARKER
        masked = True
    for group in cell.get("groups", {}).values():
        count = group.get("changed_recipients")
        if isinstance(count, (int, float)) and count > 0:
            group["changed_recipients"] = MARKER
            if group.get("model_headlines") is not None:
                group["model_headlines"] = MARKER
            masked = True
    return masked


def protect_cross_result_privacy(cola, fra, cola_ledger, fra_ledger):
    """Mask implicated FRA publication cells in place; return method text.

    Ledgers contain tuple-keyed ``events`` and ``row_events`` sets, and
    ``changed_people_by_row``, ``row_waves`` and ``admitted_people_by_row``
    maps. Compare physical person/worker identities, including overlapping
    anchor waves. COLA output and both ledgers remain unchanged. Original
    admitted denominators and reproduction checks are retained verbatim.
    Empty and already-suppressed cells keep their original representation.
    """
    left = _wave_groups(cola_ledger, cola)
    right = _wave_groups(fra_ledger, fra)
    affected_wave_support = set()
    affected_rows = set()
    for (wave, support, role), (people, workers) in right.items():
        candidates = [
            sets
            for (_, other_support, other_role), sets in left.items()
            if other_support == support and other_role == role
        ]
        for other_people, other_workers in candidates:
            if _small_difference(people, other_people) or _small_difference(
                workers, other_workers
            ):
                affected_wave_support.add((wave, support))

    cola_cells = list(_flag_cells(cola, released_only=True))
    fra_cells = list(_flag_cells(fra))
    cola_row_sets = {
        (row, support, role): _row_sets(cola_ledger, row, support, role)
        for row, support, role, _cell in cola_cells
    }
    cola_people = [
        *[people for people, _workers in left.values()],
        *[people for people, _workers in cola_row_sets.values()],
        *[
            people
            for row, people in cola_ledger["changed_people_by_row"].items()
            if _released(
                cola.get("headline_changes", {}).get(row, {}),
                "changed_recipients",
            )
        ],
        *[
            people
            for row, people in cola_ledger["admitted_people_by_row"].items()
            if _released(
                cola.get("admitted_beneficiary_counts_by_row", {}).get(
                    row, {}
                ),
                "admitted_people",
            )
        ],
    ]
    for row, support, role, _cell in fra_cells:
        if not _released(_cell):
            continue
        people, workers = _row_sets(fra_ledger, row, support, role)
        for other_row, other_support, other_role, _other_cell in cola_cells:
            if other_support != support or other_role != role:
                continue
            other_people, other_workers = cola_row_sets[
                (other_row, support, role)
            ]
            if _small_difference(people, other_people) or _small_difference(
                workers, other_workers
            ):
                affected_rows.add(row)
        for other_people in cola_people:
            if _small_difference(people, other_people):
                affected_rows.add(row)

    for row, people in fra_ledger["changed_people_by_row"].items():
        if not _released(
            fra.get("headline_changes", {}).get(row, {}),
            "changed_recipients",
        ):
            continue
        if any(_small_difference(people, other) for other in cola_people):
            affected_rows.add(row)

    # Wave totals can duplicate a row subtotal. Mask those aliases too.
    for row in affected_rows:
        wave = fra_ledger["row_waves"].get(row)
        for support in SUPPORTS:
            affected_wave_support.add((wave, support))

    for wave, cells in fra.get("counts", {}).items():
        for name, cell in cells.items():
            if "/" not in name or not isinstance(cell, dict):
                continue
            support, _role = name.split("/", 1)
            if (int(wave), support) in affected_wave_support:
                _mask_flag_cell(cell)
    for row, support, _role, cell in fra_cells:
        wave = fra_ledger["row_waves"].get(row)
        if row in affected_rows or (wave, support) in affected_wave_support:
            _mask_flag_cell(cell)
            affected_rows.add(row)
    for row, cell in fra.get("headline_changes", {}).items():
        wave = fra_ledger["row_waves"].get(row)
        if row in affected_rows or any(
            (wave, support) in affected_wave_support for support in SUPPORTS
        ):
            _mask_changes(cell)
    return (
        "Cross-result person and worker memberships were assessed for "
        "differencing. FRA flagged subtotals and positive changed-row or "
        "age cells that could disclose a residual below ten are "
        "conservatively withheld. Original admitted denominators, empty "
        "cells and reproduction checks remain."
    )
