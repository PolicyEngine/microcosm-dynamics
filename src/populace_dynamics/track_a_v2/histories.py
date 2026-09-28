"""Immutable-event supported-history adapter, a2-ratified-1 §4.6.

Opening spells are assumed to be the only unobserved pre-opening spell.
No amount is computed by this module or the structural request discovery.
"""

from collections import Counter

import pandas as pd

from populace_dynamics.cola_track_a.benefits import StateLookups


class HistoryRefusal(ValueError):
    def __init__(self, person_id, reason):
        self.person_id = person_id
        self.reason = reason
        super().__init__(f"person {person_id}: {reason}")


def nullable(value):
    return None if pd.isna(value) else int(value)


class HistoryValidator:
    """Read every immutable slice through the person's last observed slice."""

    def __init__(self, result, cohort):
        self.result = result
        self.cohort = cohort
        self.lookups = StateLookups(
            result,
            (
                int(result.slices[-1].year.iloc[0])
                if len(result.slices[-1])
                else 2030
            ),
        )
        self.rows = {
            int(pid): frame.sort_values("year", kind="stable")
            for pid, frame in result.panel.groupby("person_id", sort=True)
        }
        self.counters = Counter()
        self._validated = set()
        self.request_errors = {}

    def event_counts(self, person_id):
        rows = self.rows[person_id].iloc[1:]
        return {
            event: int((rows.di_event == event).sum())
            for event in ("award", "recovery", "conversion")
        }

    def baseline_di_record(self, person_id, state):
        """Return (eligibility, entitlement, proxy), without requesting a PIA.

        Mirrors cola_track_a/benefits.py:302–330, including the opening
        fallback and the raw-award/age-62 distinction (§4.4).
        """
        statics = self.cohort.persons_by_id.loc[person_id]
        birth = int(statics.birth_year)
        converted = nullable(state.di_conversion_year) is not None
        if not (bool(state.di_entitled) or converted):
            return None
        opener = self.cohort.opening.get(person_id)
        if (
            statics.opening_status == "disabled_worker"
            and nullable(state.di_recovery_year) is None
        ):
            if opener is None:
                year = self.cohort.start_year
                return year, year, "d_proxy_start_year_fallback"
            proxy = (
                "d_proxy_opening_age_62"
                if opener.clock_rule == "own_birth_plus_62_di"
                else "d_proxy_a3_receipt_start"
            )
            return opener.clock_year, opener.entitlement_year, proxy
        award = nullable(state.di_award_year)
        if award is None:
            raise HistoryRefusal(person_id, "DI-origin without award year")
        return (
            min(award, birth + 62),
            award,
            (
                "d_proxy_age_62_clamp"
                if award > birth + 62
                else "d_proxy_award_year"
            ),
        )

    def validate(self, person_id, eligibility_year):
        """S1–S6/O1–O5: one continuous spell with matching dates/states."""
        key = (person_id, eligibility_year)
        if key in self._validated:
            return self.baseline_di_record(
                person_id, self.rows[person_id].iloc[-1]
            )[2]
        rows = self.rows[person_id]
        first, last = rows.iloc[0], rows.iloc[-1]
        birth = int(self.cohort.persons_by_id.at[person_id, "birth_year"])
        counts = self.event_counts(person_id)

        def require(condition, message):
            if not condition:
                raise HistoryRefusal(person_id, message)

        require(
            birth >= 1913 and eligibility_year >= birth,
            "S6 helper dates unsupported",
        )
        require(
            all(int(y) > 1950 for y in self.cohort.careers.get(person_id, {})),
            "S6 history before 1951",
        )
        require(
            nullable(first.di_recovery_year) is None
            and nullable(first.di_conversion_year) is None,
            "opening recovery/conversion date is not null",
        )
        opening = bool(first.di_entitled)
        if opening:
            require(
                counts["award"] == 0, "O2 projected award after opening DI"
            )
            start = int(first.year)
        else:
            require(
                nullable(first.di_award_year) is None,
                "S1 opening award date is not null",
            )
            require(counts["award"] == 1, "S2 requires one projected award")
            start = int(rows.loc[rows.di_event == "award", "year"].iloc[0])
            require(
                nullable(last.di_award_year) == start,
                "S2 final award date disagrees",
            )
        require(
            counts["recovery"] == 0
            and nullable(last.di_recovery_year) is None,
            "S3/O2 recovery is unsupported",
        )
        require(counts["conversion"] <= 1, "S4/O3 multiple conversions")
        converted = rows.loc[rows.di_event == "conversion", "year"]
        conversion = None if converted.empty else int(converted.iloc[0])
        require(
            nullable(last.di_conversion_year) == conversion,
            "S4/O3 final conversion date disagrees",
        )
        require(
            conversion is None or conversion > start,
            "S4/O3 conversion without prior entitlement",
        )
        opening_award = nullable(first.di_award_year)
        for _, state in rows.iterrows():
            year = int(state.year)
            expected = year >= start and (
                conversion is None or year < conversion
            )
            require(
                bool(state.di_entitled) == expected,
                "S5/O3 entitlement state disagrees with events",
            )
            expected_award = (
                opening_award
                if opening
                else (start if year >= start else None)
            )
            require(
                nullable(state.di_award_year) == expected_award,
                "award field disagrees with event history",
            )
            require(
                nullable(state.di_recovery_year) is None,
                "recovery field disagrees with event history",
            )
            require(
                nullable(state.di_conversion_year)
                == (
                    conversion
                    if conversion is not None and year >= conversion
                    else None
                ),
                "conversion field disagrees with event history",
            )
        record = self.baseline_di_record(person_id, last)
        require(
            record is not None, "requested DI level lacks DI-origin record"
        )
        self._validated.add(key)
        self.counters[record[2]] += 1
        return record[2]

    def requested_di_levels(self):
        """Discover own/linked/deceased DI requests without level arithmetic.

        §4.6 scope is the union of reached requests under all rows and
        mechanisms. Eligibility-before-1979 paths end before auxiliary
        requests (cola_track_a/benefits.py:553–557), as does no own record.
        """
        requested = {}
        statics = self.cohort.persons_by_id
        reference = self.lookups.reference_year

        self.request_errors = {}

        def request(pid, state):
            try:
                record = self.baseline_di_record(pid, state)
            except HistoryRefusal as exc:
                self.request_errors[pid] = exc
                # §4.6: count every structurally reached unsupported record.
                # This sentinel continues discovery only, never a level or
                # fallback. The joint validator still refuses the record.
                year = int(statics.at[pid, "birth_year"]) + 62
                return year, year, "unsupported_missing_award"
            if record is not None and record[0] >= 1979:
                requested[pid] = record[0]
            return record

        for pid in sorted(int(i) for i in self.lookups.final.index):
            state = self.lookups.final.loc[pid]
            opener = self.cohort.opening.get(pid)
            if opener and not (
                opener.status == "disabled_worker"
                and nullable(state.di_recovery_year) is not None
            ):
                continue
            own = request(pid, state)
            own_exists = own is not None or (
                bool(state.claimed)
                and nullable(state.claim_year) is not None
                and str(statics.at[pid, "opening_status"])
                not in ("survivor", "spouse", "other", "unclassified")
            )
            if own is not None and own[0] < 1979:
                continue
            if (
                own is None
                and own_exists
                and int(statics.at[pid, "birth_year"]) + 62 < 1979
            ):
                # Own retirement level unavailable: v1 returns before auxiliaries.
                continue
            if state.marital_status == "married" and own_exists:
                linked = nullable(state.spouse_person_id)
                if linked in self.cohort.roster_ids and self.lookups.alive(
                    linked
                ):
                    request(linked, self.lookups.final.loc[linked])
            elif state.marital_status == "widowed":
                linked = nullable(state.late_spouse_person_id)
                death = nullable(state.widowhood_year)
                if (
                    linked in self.cohort.roster_ids
                    and death is not None
                    and self.lookups.death_year(linked) == death
                    and max(death, int(statics.at[pid, "birth_year"]) + 60)
                    <= reference
                ):
                    request(linked, self.lookups.last.loc[linked])
        return requested

    def requested_di_ids(self):
        return tuple(self.requested_di_levels())

    def validate_requested(self):
        levels = self.requested_di_levels()
        for pid in sorted(set(levels) | set(self.request_errors)):
            try:
                if pid in self.request_errors:
                    raise self.request_errors[pid]
                self.validate(pid, levels[pid])
            except HistoryRefusal as exc:
                exc.counters = dict(self.counters)
                raise
        return self.counters.copy()
