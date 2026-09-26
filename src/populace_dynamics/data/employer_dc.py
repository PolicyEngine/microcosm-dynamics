"""Label-verified PSID employer DC account balances, waves 2005-2013.

DynaSim scorecard exercise 2 ("Track U", specification
``docs/design/boomers2004_uniform_cut_comparison.md``) annuitizes 80
percent of a family's financial assets.  The Report's financial assets are
non-pension wealth "as well as IRA, Keogh, and 401(k) balances" (printed
p. 24, as quoted in the cleared exercise-2 definitions extract), and it
contrasts them with the Census measure, under which retirement "account
balances that are left to accumulate are excluded altogether" (same
page).  PSID's WEALTH1 (:mod:`populace_dynamics.data.family_income`) holds
IRAs and private annuities (W22) but no employer defined-contribution
(DC) account held outside an IRA.  Row U7 adds the employer DC balances
the PSID pension section (the P section of the family file) observes.
This module reads them.

Label investigation, 2026-09-25, against the staged ``.sps`` setup files
and the family codebooks of 2005, 2007, 2009, 2011 and 2013 (question
text, value codes and ``Inap.`` universes; the codebooks' whole-sample
frequency counts were seen and not used), and, in the independent review
of ``u1-draft-7`` (2026-09-25), the questionnaires' routing of the
previous-employer items (P45-P69):

* **Who is asked.** The head and the wife (the family file's "wife"
  includes a cohabiting partner).  OFUMs are not asked the section.  The
  previous-employer items (P45 on) are asked of everyone who has ever
  worked for money ("Inap.: has never worked for money"), so retirees are
  asked too; the current-job items (P16 on) only of a head or wife working
  now and covered by a plan on the present job.
* **Current job** (head P20, wife P90 before 2011; "P20 ... - HD" and
  "- WF" from 2011): "What is the approximate dollar amount in your
  account now?", asked when the plan bases benefits on an account or on
  both a formula and an account (P16/P86 "HOW BENEFIT FIGURED": 3 "Both"
  or 5 "Money accumulated in account" before 2011; 5 "Defined
  contribution plan" or 7 "Both" from 2011).  P20's ``Inap.`` text names
  "defined benefit formula only" and "NA, DK whether defined benefit
  formula, money accumulated or accrued, or both", so P16/P86 routes the
  item here.  (The interviewer checkpoint P22/P92, "CKPT: TYPE PENSION",
  is 0 for some records with an amount: 2 head and 1 wife records in
  2005, 2 head in 2009, 1 head and 1 wife in 2011, 85 head and 37 wife in
  2013, whole file; this reader does not read it.)  A second
  tax-deferred plan on the same job (P42, "a 'thrift', profit-sharing, or
  Keogh plan") has no balance item.
* **Previous employers, up to two plans each** (``#1``, ``#2``; a third,
  P69 "WTR 3RD PREV PENSION" before 2013, has no amounts).  The plan type
  (P46/P116: before 2011 1 "Type A" formula, 2 "Type B" account, 3 "Both
  types"; from 2011 1 "Defined benefit", 5 "Defined contribution", 7
  "Both"; 8 DK, 9 NA) routes the questions.  The questionnaires (the
  PSID "box and arrow" instruments ``q2005``, ``q2009``, ``q2011`` and
  ``q2013``; no 2007 instrument is staged) route them so:

  - a "both" plan is asked the "both" items: P47/P117 (the account when
    the person left), P48/P118 (what was done with it: 1 "withdrew", 2
    "rolled over into IRA", 3 "left to accumulate", 4 "converted to
    annuity", 7 "other") and, after codes 2 and 3, P49/P119 "How much is
    in your account now?"; then the formula part.  The codebooks'
    ``Inap.`` texts agree ("Type A or B plan, DK or refused type" before
    2011; types 1, 5, 8 and 9 from 2011);
  - a formula, "both" or DK-type plan is asked the formula part (P52 on:
    status, benefits, and, when future benefits are expected, P62 "Can
    you estimate what you expect these benefits to be?"); a DC ("Type
    B") plan skips it;
  - the account items, P63/P133 (the account when the person left),
    P64/P134 (1 "Transferred to new employer", 2 "Rolled over into IRA",
    3 "Left to accumulate", 4 "Converted to annuity", 7 "Other") and,
    after codes 2 and 3, P65/P135 "How much is in your account now?",
    follow checkpoint P62A ("whether pension is DC (P46=5) or DB amount
    is DK/RF"): they are asked of a DC plan *and of any formula, "both"
    or DK-type plan whose expected benefit at P62 is DK or refused*.

  The codebooks' ``Inap.`` texts of P63-P65 ("Type A or combination plan
  or refused type" before 2011; types 1, 7 and 9 from 2011) leave out
  the checkpoint's second branch, but the staged files follow the
  questionnaires: in every wave a formula- or DK-type plan has a recorded
  P64/P134 exactly when its P62/P132 amount (or, before 2011, lump sum)
  is DK or refused, and every "both" plan with a DK or refused P62/P132
  has one (independent review of ``u1-draft-7``, 2026-09-25, structural
  counts; ``tests/data/test_employer_dc_integration.py``).  So a formula-type
  plan's account items are on the instrument's route exactly as a
  DK-type plan's are.  The question introducing
  previous-employer plans changes from "were you included in a pension or
  retirement plan, or in any tax-deferred savings plan, through a former
  employer?" (2005-2009) to "have any pensions or retirement plans from
  previous employers from which you expect to receive benefits?" (2011;
  2013 adds "[have/has not begun to receive regular benefit payments
  but]").
* **Codes of the amounts.** P20/P90 are 9 digits: 1-999,999,996 actual
  amount, 999,999,997 "$999,999,997 or more", 999,999,998 DK,
  999,999,999 "NA; refused", 0 Inap. (which includes "no money
  accumulated yet").  P49/P65 (and the wife's) are 8 digits with the
  same pattern (99,999,996 ... 99,999,999).  The amounts are as reported:
  unlike WEALTH1 they are not imputed; from 2007 a DK or refusal is
  followed by bracket questions (``P20B WTR AMT GE 10,000`` and so on),
  which this reader does not use.

**The U7 balance** (:func:`employer_dc_balances`), per family, head and
wife together, follows the questionnaires' route item by item: the
current-job amount when P16/P86 names an account or combined plan; plus,
for each previous plan, the amount now when the account was *left to
accumulate* (code 3) in the old employer's plan, from the "both" items of
a "both" plan and from the account items of a DC, formula or DK-type
plan.  A "both" plan's account items are not counted: its account is
asked at P47-P49, and checkpoint P62A asks P63-P65 again when its
expected benefit is DK or refused (69 previous plans over the five waves
carry both a P49 and a P65 amount, every one a "both" plan and 44 with
equal codes), so counting both could count one account twice.  An
account *rolled over into an IRA* (code 2) on the route is excluded: its
"now" amount is an IRA balance, which WEALTH1 already holds (W22,
"private annuities or Individual Retirement Accounts"), and it is counted
in ``employer_dc_ira_rollover_items``.  A nonzero amount U7 does not take
(a current-job amount whose P16/P86 names no account; a previous plan's
amount left to accumulate in items U7 does not route to the plan's type:
the "both" items of a plan that is not "both", the account items of a
"both" plan, any item under an NA or Inap. type) is excluded and counted
in ``employer_dc_off_route_items``.  Accounts withdrawn, converted to an
annuity, transferred to a new employer or "other" have no amount now.  A
DK or refused amount on the route counts as 0 and is counted in
``employer_dc_unreported``; the top code counts as recorded.

Until the independent review of ``u1-draft-7`` (2026-09-25) the rule
followed the codebooks' ``Inap.`` texts and left out the account items of
formula-type plans while counting those of DK-type plans; the
questionnaires route the two identically (above), so both are counted.

What this module does not do: it computes no annuity, income, threshold
or poverty status, and it attaches nothing to persons (see
:mod:`populace_dynamics.cohorts.age67`).  An OFUM's employer DC account
is never observed.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from populace_dynamics.data import family, family_income, psid

__all__ = [
    "AMOUNT_WIDTHS",
    "BALANCE_COLUMNS",
    "COUNTED_DISPOSITION",
    "DISPOSITION_CODES",
    "EMPLOYER_DC_WAVES",
    "EXCLUDED_IRA_DISPOSITION",
    "PERSONS",
    "PREVIOUS_DK_TYPE",
    "PREVIOUS_FORMULA_TYPE",
    "PREVIOUS_PLANS",
    "amount_codes",
    "employer_dc_balances",
    "employer_dc_variables",
    "plan_type_codes",
    "read_employer_dc",
    "reconcile_employer_dc",
]

#: Waves whose family file this module reads (the Track U waves).
EMPLOYER_DC_WAVES: tuple[int, ...] = family_income.INCOME_WAVES
PERSONS: tuple[str, ...] = ("head", "wife")
#: The previous-employer plans the P section asks amounts for.
PREVIOUS_PLANS: tuple[int, ...] = (1, 2)
#: Waves asked with the 2011 wording and codes ("- HD", "- WF").
_NEW_CODES_WAVES: frozenset[int] = frozenset({2011, 2013})
#: Current-job plan type (P16/P86 "HOW BENEFIT FIGURED") codes, and
#: those whose plan has an account (the universe of P20/P90).
_CURRENT_TYPE_CODES: dict[bool, tuple[int, ...]] = {
    False: (0, 1, 3, 5, 8, 9),
    True: (0, 1, 5, 7, 8, 9),
}
_CURRENT_ACCOUNT_TYPES: dict[bool, tuple[int, ...]] = {
    False: (3, 5),
    True: (5, 7),
}
#: Previous-plan type (P46/P116) codes, and the "both" and account-only
#: codes that route P48-P49 and P64-P65.
_PREVIOUS_TYPE_CODES: dict[bool, tuple[int, ...]] = {
    False: (0, 1, 2, 3, 8, 9),
    True: (0, 1, 5, 7, 8, 9),
}
_PREVIOUS_BOTH_TYPE: dict[bool, int] = {False: 3, True: 7}
_PREVIOUS_ACCOUNT_TYPE: dict[bool, int] = {False: 2, True: 5}
#: Formula ("Type A", defined benefit) plan type, 1 in every wave: the
#: questionnaires ask its account items (P63-P65) when its expected
#: benefit (P62) is DK or refused, as for a DK-type plan.
PREVIOUS_FORMULA_TYPE = 1
#: "DK" plan type: the questionnaires route it through the formula part
#: to the account items (P63-P65) when its expected benefit is DK or
#: refused, in every wave, and never to the "both" items (P47-P49).
PREVIOUS_DK_TYPE = 8
#: What was done with a previous plan's account (P48/P64 and the wife's).
DISPOSITION_CODES: tuple[int, ...] = (0, 1, 2, 3, 4, 7, 8, 9)
#: "Left to accumulate" in the old plan: the amount now counts.
COUNTED_DISPOSITION = 3
#: "Rolled over into IRA": the amount now is an IRA balance (W22).
EXCLUDED_IRA_DISPOSITION = 2
#: Field width of each amount concept (the codebooks' NUM(w.0)).
AMOUNT_WIDTHS: dict[str, int] = {
    "current_amount": 9,
    "combo_amount": 8,
    "dc_amount": 8,
}
#: The derived per-family columns :func:`employer_dc_balances` adds.
BALANCE_COLUMNS: tuple[str, ...] = (
    "employer_dc",
    "employer_dc_current",
    "employer_dc_previous",
    "employer_dc_items",
    "employer_dc_unreported",
    "employer_dc_top_coded",
    "employer_dc_ira_rollover_items",
    "employer_dc_off_route_items",
)

#: The adjudicated ``{concept: (variable, label)}`` tables, verified
#: against each wave's ``.sps`` labels at read time.
_VARS: dict[int, dict[str, tuple[str, str]]] = {
    2005: {
        "head_current_type": ("ER26719", "P16 HOW BENEFIT FIGURED"),
        "head_current_amount": ("ER26725", "P20 AMT IN PENSION ACCT NOW"),
        "head_prev1_type": ("ER26764", "P46 TYPE PREV PENSION-#1"),
        "head_prev1_combo_disposition": (
            "ER26766",
            "P48 WHAT DID W/PREV PNSN-#1",
        ),
        "head_prev1_combo_amount": (
            "ER26767",
            "P49 AMT NOW PREV PNSN ACCT-#1",
        ),
        "head_prev1_dc_disposition": (
            "ER26798",
            "P64 WHAT DID W/PREV PNSN-#1",
        ),
        "head_prev1_dc_amount": ("ER26799", "P65 ACCT AMT PREV PNSN NOW-#1"),
        "head_prev2_type": ("ER26805", "P46 TYPE PREV PENSION-#2"),
        "head_prev2_combo_disposition": (
            "ER26807",
            "P48 WHAT DID W/PREV PNSN-#2",
        ),
        "head_prev2_combo_amount": (
            "ER26808",
            "P49 AMT NOW PREV PNSN ACCT-#2",
        ),
        "head_prev2_dc_disposition": (
            "ER26839",
            "P64 WHAT DID W/PREV PNSN-#2",
        ),
        "head_prev2_dc_amount": ("ER26840", "P65 ACCT AMT PREV PNSN NOW-#2"),
        "wife_current_type": ("ER26863", "P86 HOW BENEFIT FIGURED"),
        "wife_current_amount": ("ER26869", "P90 AMT IN PENSION ACCT NOW"),
        "wife_prev1_type": ("ER26908", "P116 TYPE PREV PENSION-#1"),
        "wife_prev1_combo_disposition": (
            "ER26910",
            "P118 WHAT DID W/PREV PNSN-#1",
        ),
        "wife_prev1_combo_amount": (
            "ER26911",
            "P119 AMT NOW PREV PNSN ACCT-#1",
        ),
        "wife_prev1_dc_disposition": (
            "ER26942",
            "P134 WHAT DID W/PREV PNSN-#1",
        ),
        "wife_prev1_dc_amount": (
            "ER26943",
            "P135 ACCT AMT PREV PNSN NOW-#1",
        ),
        "wife_prev2_type": ("ER26949", "P116 TYPE PREV PENSION-#2"),
        "wife_prev2_combo_disposition": (
            "ER26951",
            "P118 WHAT DID W/PREV PNSN-#2",
        ),
        "wife_prev2_combo_amount": (
            "ER26952",
            "P119 AMT NOW PREV PNSN ACCT-#2",
        ),
        "wife_prev2_dc_disposition": (
            "ER26983",
            "P134 WHAT DID W/PREV PNSN-#2",
        ),
        "wife_prev2_dc_amount": (
            "ER26984",
            "P135 ACCT AMT PREV PNSN NOW-#2",
        ),
    },
    2007: {
        "head_current_type": ("ER37755", "P16 HOW BENEFIT FIGURED"),
        "head_current_amount": ("ER37761", "P20 AMT IN PENSION ACCT NOW"),
        "head_prev1_type": ("ER37808", "P46 TYPE PREV PENSION-#1"),
        "head_prev1_combo_disposition": (
            "ER37814",
            "P48 WHAT DID W/PREV PNSN-#1",
        ),
        "head_prev1_combo_amount": (
            "ER37815",
            "P49 AMT NOW PREV PNSN ACCT-#1",
        ),
        "head_prev1_dc_disposition": (
            "ER37874",
            "P64 WHAT DID W/PREV PNSN-#1",
        ),
        "head_prev1_dc_amount": ("ER37875", "P65 ACCT AMT PREV PNSN NOW-#1"),
        "head_prev2_type": ("ER37889", "P46 TYPE PREV PENSION-#2"),
        "head_prev2_combo_disposition": (
            "ER37895",
            "P48 WHAT DID W/PREV PNSN-#2",
        ),
        "head_prev2_combo_amount": (
            "ER37896",
            "P49 AMT NOW PREV PNSN ACCT-#2",
        ),
        "head_prev2_dc_disposition": (
            "ER37955",
            "P64 WHAT DID W/PREV PNSN-#2",
        ),
        "head_prev2_dc_amount": ("ER37956", "P65 ACCT AMT PREV PNSN NOW-#2"),
        "wife_current_type": ("ER37987", "P86 HOW BENEFIT FIGURED"),
        "wife_current_amount": ("ER37993", "P90 AMT IN PENSION ACCT NOW"),
        "wife_prev1_type": ("ER38040", "P116 TYPE PREV PENSION-#1"),
        "wife_prev1_combo_disposition": (
            "ER38046",
            "P118 WHAT DID W/PREV PNSN-#1",
        ),
        "wife_prev1_combo_amount": (
            "ER38047",
            "P119 AMT NOW PREV PNSN ACCT-#1",
        ),
        "wife_prev1_dc_disposition": (
            "ER38106",
            "P134 WHAT DID W/PREV PNSN-#1",
        ),
        "wife_prev1_dc_amount": (
            "ER38107",
            "P135 ACCT AMT PREV PNSN NOW-#1",
        ),
        "wife_prev2_type": ("ER38121", "P116 TYPE PREV PENSION-#2"),
        "wife_prev2_combo_disposition": (
            "ER38127",
            "P118 WHAT DID W/PREV PNSN-#2",
        ),
        "wife_prev2_combo_amount": (
            "ER38128",
            "P119 AMT NOW PREV PNSN ACCT-#2",
        ),
        "wife_prev2_dc_disposition": (
            "ER38187",
            "P134 WHAT DID W/PREV PNSN-#2",
        ),
        "wife_prev2_dc_amount": (
            "ER38188",
            "P135 ACCT AMT PREV PNSN NOW-#2",
        ),
    },
    2009: {
        "head_current_type": ("ER43728", "P16 HOW BENEFIT FIGURED"),
        "head_current_amount": ("ER43734", "P20 AMT IN PENSION ACCT NOW"),
        "head_prev1_type": ("ER43781", "P46 TYPE PREV PENSION-#1"),
        "head_prev1_combo_disposition": (
            "ER43787",
            "P48 WHAT DID W/PREV PNSN-#1",
        ),
        "head_prev1_combo_amount": (
            "ER43788",
            "P49 AMT NOW PREV PNSN ACCT-#1",
        ),
        "head_prev1_dc_disposition": (
            "ER43847",
            "P64 WHAT DID W/PREV PNSN-#1",
        ),
        "head_prev1_dc_amount": ("ER43848", "P65 ACCT AMT PREV PNSN NOW-#1"),
        "head_prev2_type": ("ER43862", "P46 TYPE PREV PENSION-#2"),
        "head_prev2_combo_disposition": (
            "ER43868",
            "P48 WHAT DID W/PREV PNSN-#2",
        ),
        "head_prev2_combo_amount": (
            "ER43869",
            "P49 AMT NOW PREV PNSN ACCT-#2",
        ),
        "head_prev2_dc_disposition": (
            "ER43928",
            "P64 WHAT DID W/PREV PNSN-#2",
        ),
        "head_prev2_dc_amount": ("ER43929", "P65 ACCT AMT PREV PNSN NOW-#2"),
        "wife_current_type": ("ER43960", "P86 HOW BENEFIT FIGURED"),
        "wife_current_amount": ("ER43966", "P90 AMT IN PENSION ACCT NOW"),
        "wife_prev1_type": ("ER44013", "P116 TYPE PREV PENSION-#1"),
        "wife_prev1_combo_disposition": (
            "ER44019",
            "P118 WHAT DID W/PREV PNSN-#1",
        ),
        "wife_prev1_combo_amount": (
            "ER44020",
            "P119 AMT NOW PREV PNSN ACCT-#1",
        ),
        "wife_prev1_dc_disposition": (
            "ER44079",
            "P134 WHAT DID W/PREV PNSN-#1",
        ),
        "wife_prev1_dc_amount": (
            "ER44080",
            "P135 ACCT AMT PREV PNSN NOW-#1",
        ),
        "wife_prev2_type": ("ER44094", "P116 TYPE PREV PENSION-#2"),
        "wife_prev2_combo_disposition": (
            "ER44100",
            "P118 WHAT DID W/PREV PNSN-#2",
        ),
        "wife_prev2_combo_amount": (
            "ER44101",
            "P119 AMT NOW PREV PNSN ACCT-#2",
        ),
        "wife_prev2_dc_disposition": (
            "ER44160",
            "P134 WHAT DID W/PREV PNSN-#2",
        ),
        "wife_prev2_dc_amount": (
            "ER44161",
            "P135 ACCT AMT PREV PNSN NOW-#2",
        ),
    },
    2011: {
        "head_current_type": ("ER49074", "P16 HOW BENEFIT FIGURED - HD"),
        "head_current_amount": (
            "ER49080",
            "P20 AMT IN PENSION ACCT NOW - HD",
        ),
        "head_prev1_type": ("ER49115", "P46 TYPE PREV PENSION-#1 - HD"),
        "head_prev1_combo_disposition": (
            "ER49121",
            "P48 WHAT DID W/PREV PNSN-#1 - HD",
        ),
        "head_prev1_combo_amount": (
            "ER49122",
            "P49 AMT NOW PREV PNSN ACCT-#1 - HD",
        ),
        "head_prev1_dc_disposition": (
            "ER49180",
            "P64 WHAT DID W/PREV PNSN-#1 - HD",
        ),
        "head_prev1_dc_amount": (
            "ER49181",
            "P65 ACCT AMT PREV PNSN NOW-#1 - HD",
        ),
        "head_prev2_type": ("ER49195", "P46 TYPE PREV PENSION-#2 - HD"),
        "head_prev2_combo_disposition": (
            "ER49201",
            "P48 WHAT DID W/PREV PNSN-#2 - HD",
        ),
        "head_prev2_combo_amount": (
            "ER49202",
            "P49 AMT NOW PREV PNSN ACCT-#2 - HD",
        ),
        "head_prev2_dc_disposition": (
            "ER49260",
            "P64 WHAT DID W/PREV PNSN-#2 - HD",
        ),
        "head_prev2_dc_amount": (
            "ER49261",
            "P65 ACCT AMT PREV PNSN NOW-#2 - HD",
        ),
        "wife_current_type": ("ER49293", "P16 HOW BENEFIT FIGURED - WF"),
        "wife_current_amount": (
            "ER49299",
            "P20 AMT IN PENSION ACCT NOW - WF",
        ),
        "wife_prev1_type": ("ER49334", "P46 TYPE PREV PENSION-#1 - WF"),
        "wife_prev1_combo_disposition": (
            "ER49340",
            "P48 WHAT DID W/PREV PNSN-#1 - WF",
        ),
        "wife_prev1_combo_amount": (
            "ER49341",
            "P49 AMT NOW PREV PNSN ACCT-#1 - WF",
        ),
        "wife_prev1_dc_disposition": (
            "ER49399",
            "P64 WHAT DID W/PREV PNSN-#1 - WF",
        ),
        "wife_prev1_dc_amount": (
            "ER49400",
            "P65 ACCT AMT PREV PNSN NOW-#1 - WF",
        ),
        "wife_prev2_type": ("ER49414", "P46 TYPE PREV PENSION-#2 - WF"),
        "wife_prev2_combo_disposition": (
            "ER49420",
            "P48 WHAT DID W/PREV PNSN-#2 - WF",
        ),
        "wife_prev2_combo_amount": (
            "ER49421",
            "P49 AMT NOW PREV PNSN ACCT-#2 - WF",
        ),
        "wife_prev2_dc_disposition": (
            "ER49479",
            "P64 WHAT DID W/PREV PNSN-#2 - WF",
        ),
        "wife_prev2_dc_amount": (
            "ER49480",
            "P65 ACCT AMT PREV PNSN NOW-#2 - WF",
        ),
    },
    2013: {
        "head_current_type": ("ER54828", "P16 HOW BENEFIT FIGURED - HD"),
        "head_current_amount": (
            "ER54836",
            "P20 AMT IN PENSION ACCT NOW - HD",
        ),
        "head_prev1_type": ("ER54869", "P46 TYPE PREV PENSION-#1 - HD"),
        "head_prev1_combo_disposition": (
            "ER54875",
            "P48 WHAT DID W/PREV PNSN-#1 - HD",
        ),
        "head_prev1_combo_amount": (
            "ER54876",
            "P49 AMT NOW PREV PNSN ACCT-#1 - HD",
        ),
        "head_prev1_dc_disposition": (
            "ER54935",
            "P64 WHAT DID W/PREV PNSN-#1 - HD",
        ),
        "head_prev1_dc_amount": (
            "ER54936",
            "P65 ACCT AMT PREV PNSN NOW-#1 - HD",
        ),
        "head_prev2_type": ("ER54949", "P46 TYPE PREV PENSION-#2 - HD"),
        "head_prev2_combo_disposition": (
            "ER54955",
            "P48 WHAT DID W/PREV PNSN-#2 - HD",
        ),
        "head_prev2_combo_amount": (
            "ER54956",
            "P49 AMT NOW PREV PNSN ACCT-#2 - HD",
        ),
        "head_prev2_dc_disposition": (
            "ER55015",
            "P64 WHAT DID W/PREV PNSN-#2 - HD",
        ),
        "head_prev2_dc_amount": (
            "ER55016",
            "P65 ACCT AMT PREV PNSN NOW-#2 - HD",
        ),
        "wife_current_type": ("ER55044", "P16 HOW BENEFIT FIGURED - WF"),
        "wife_current_amount": (
            "ER55052",
            "P20 AMT IN PENSION ACCT NOW - WF",
        ),
        "wife_prev1_type": ("ER55085", "P46 TYPE PREV PENSION-#1 - WF"),
        "wife_prev1_combo_disposition": (
            "ER55091",
            "P48 WHAT DID W/PREV PNSN-#1 - WF",
        ),
        "wife_prev1_combo_amount": (
            "ER55092",
            "P49 AMT NOW PREV PNSN ACCT-#1 - WF",
        ),
        "wife_prev1_dc_disposition": (
            "ER55151",
            "P64 WHAT DID W/PREV PNSN-#1 - WF",
        ),
        "wife_prev1_dc_amount": (
            "ER55152",
            "P65 ACCT AMT PREV PNSN NOW-#1 - WF",
        ),
        "wife_prev2_type": ("ER55165", "P46 TYPE PREV PENSION-#2 - WF"),
        "wife_prev2_combo_disposition": (
            "ER55171",
            "P48 WHAT DID W/PREV PNSN-#2 - WF",
        ),
        "wife_prev2_combo_amount": (
            "ER55172",
            "P49 AMT NOW PREV PNSN ACCT-#2 - WF",
        ),
        "wife_prev2_dc_disposition": (
            "ER55231",
            "P64 WHAT DID W/PREV PNSN-#2 - WF",
        ),
        "wife_prev2_dc_amount": (
            "ER55232",
            "P65 ACCT AMT PREV PNSN NOW-#2 - WF",
        ),
    },
}


def _new_codes(wave: int) -> bool:
    return int(wave) in _NEW_CODES_WAVES


def plan_type_codes(wave: int) -> dict[str, int]:
    """The plan-type codes of a wave: current and previous plans.

    ``current_account`` and ``current_both`` (P16/P86: an account plan and
    a plan with both a formula and an account), ``previous_formula``,
    ``previous_account``, ``previous_both`` and ``previous_dk``
    (P46/P116).  The codes change in 2011 (for example "Both" is 3 before
    2011 and 7 from 2011); DK is 8 in every wave.
    """

    new = _new_codes(int(wave))
    return {
        "current_account": 5,
        "current_both": 7 if new else 3,
        "previous_formula": PREVIOUS_FORMULA_TYPE,
        "previous_account": _PREVIOUS_ACCOUNT_TYPE[new],
        "previous_both": _PREVIOUS_BOTH_TYPE[new],
        "previous_dk": PREVIOUS_DK_TYPE,
    }


def employer_dc_variables(wave: int) -> dict[str, tuple[str, str]]:
    """The adjudicated ``{concept: (variable, label)}`` table of a wave.

    The family interview number (``interview``, from
    :func:`populace_dynamics.data.family_income.income_variables`) and, for
    ``head`` and ``wife``, the current-job plan checkpoint and account
    amount and, for previous plans 1 and 2, the plan type, the disposition
    and account amount now of a "both" plan (``combo``) and of an
    account-only plan (``dc``).
    """

    wave = int(wave)
    if wave not in _VARS:
        raise ValueError(
            f"Wave {wave} is outside the resolved employer DC waves "
            f"{EMPLOYER_DC_WAVES}."
        )
    interview = family_income.income_variables(wave)["interview"]
    return {"interview": interview, **_VARS[wave]}


def amount_codes(width: int) -> dict[str, int]:
    """The codebook's amount codes for a ``NUM(width.0)`` amount item.

    ``top`` ("$...997 or more"), ``dk`` and ``na`` ("NA; refused"); every
    positive value below ``top`` is an actual amount and 0 is Inap.
    """

    width = int(width)
    if width < 2:
        raise ValueError("an amount field has at least two digits")
    ceiling = 10**width
    return {"top": ceiling - 3, "dk": ceiling - 2, "na": ceiling - 1}


def _kind(concept: str) -> str:
    """The item kind of a concept (``current_amount``, ``dc_amount`` ...)."""

    for kind in (
        "current_type",
        "current_amount",
        "combo_disposition",
        "combo_amount",
        "dc_disposition",
        "dc_amount",
    ):
        if concept.endswith(kind):
            return kind
    if concept.endswith("_type"):
        return "previous_type"
    raise ValueError(f"unknown employer DC concept {concept!r}")


def _allowed_codes(kind: str, wave: int) -> tuple[int, ...] | None:
    new = _new_codes(wave)
    if kind == "current_type":
        return _CURRENT_TYPE_CODES[new]
    if kind == "previous_type":
        return _PREVIOUS_TYPE_CODES[new]
    if kind in ("combo_disposition", "dc_disposition"):
        return DISPOSITION_CODES
    return None


def _check_codes(frame: pd.DataFrame, wave: int, context: str) -> None:
    for concept in _VARS[wave]:
        kind = _kind(concept)
        values = frame[concept]
        allowed = _allowed_codes(kind, wave)
        if allowed is not None:
            codes = set(int(code) for code in pd.unique(values))
            if not codes <= set(allowed):
                raise ValueError(
                    f"{context}: undocumented code(s) "
                    f"{sorted(codes - set(allowed))} in {concept}"
                )
        else:
            ceiling = 10 ** AMOUNT_WIDTHS[kind]
            if ((values < 0) | (values >= ceiling)).any():
                raise ValueError(
                    f"{context}: {concept} outside 0-{ceiling - 1}"
                )


def _decoded(amount: np.ndarray, width: int) -> tuple[np.ndarray, ...]:
    """(counted value, reported, unreported, top-coded) of amounts."""

    codes = amount_codes(width)
    unreported = (amount == codes["dk"]) | (amount == codes["na"])
    reported = (amount > 0) & ~unreported
    value = np.where(reported, amount, 0).astype(np.int64)
    top = amount == codes["top"]
    return value, reported, unreported, top


def _account_route(part: str, plan_type: np.ndarray, wave: int) -> np.ndarray:
    """Whether U7 takes a previous plan's ``part`` items for its type.

    The "both" items (``combo``: P48-P49, P118-P119) for a "both" plan
    only; the account items (``dc``: P64-P65, P134-P135) for a DC plan and
    for a formula or DK-type plan, which the questionnaires' checkpoint
    P62A asks them of when its expected benefit is DK or refused.  A
    "both" plan's account items re-ask the account its "both" items hold,
    so U7 does not take them (module docstring).
    """

    new = _new_codes(wave)
    if part == "combo":
        return plan_type == _PREVIOUS_BOTH_TYPE[new]
    return np.isin(
        plan_type,
        (_PREVIOUS_ACCOUNT_TYPE[new], PREVIOUS_FORMULA_TYPE, PREVIOUS_DK_TYPE),
    )


def employer_dc_balances(raw: pd.DataFrame, wave: int) -> pd.DataFrame:
    """The U7 balance of each family from its P-section items.

    ``raw`` holds one row per family with ``interview`` and every concept
    of :func:`employer_dc_variables` (as recorded, codes and amounts).
    Returns ``raw`` with the columns of :data:`BALANCE_COLUMNS` added:

    * ``employer_dc_current``: the head's and wife's current-job account
      amounts (P20, P90) where the plan type (P16, P86) has an account;
    * ``employer_dc_previous``: for each previous plan 1 and 2 of the head
      and wife, the account amount now when the account was left to
      accumulate (disposition :data:`COUNTED_DISPOSITION`), on the
      questionnaires' route: the "both" items (P48-P49) of a "both" plan,
      the account items (P64-P65) of a DC plan or of a formula or DK-type
      plan (:data:`PREVIOUS_FORMULA_TYPE`, :data:`PREVIOUS_DK_TYPE`);
    * ``employer_dc``: their sum;
    * ``employer_dc_items``: the counted amounts that are positive;
    * ``employer_dc_unreported``: counted items whose amount is DK or
      refused (valued at 0);
    * ``employer_dc_top_coded``: counted items at the top code (valued as
      recorded);
    * ``employer_dc_ira_rollover_items``: previous-plan accounts on the
      route rolled over into an IRA (disposition
      :data:`EXCLUDED_IRA_DISPOSITION`), whose amount now is not counted
      because WEALTH1 holds IRAs;
    * ``employer_dc_off_route_items``: nonzero amounts not counted because
      U7 does not take the item for the plan's type (a current-job amount
      whose P16/P86 names no account; a previous plan's amount left to
      accumulate in the "both" items of a plan that is not "both", under
      an NA or Inap. type, or in the account items P64-P65 of a "both"
      plan, which re-ask the account its "both" items P48-P49 hold).

    Every other disposition (withdrawn, converted to an annuity,
    transferred to a new employer, other, DK, refused) and a plan whose
    amount the P section did not ask count nothing.
    """

    wave = int(wave)
    concepts = list(_VARS[wave])
    missing = [c for c in ("interview", *concepts) if c not in raw.columns]
    if missing:
        raise ValueError(f"employer DC {wave}: rows lack {missing}")
    n = len(raw)
    new = _new_codes(wave)
    current = np.zeros(n, dtype=np.int64)
    previous = np.zeros(n, dtype=np.int64)
    items = np.zeros(n, dtype=np.int64)
    unreported = np.zeros(n, dtype=np.int64)
    top = np.zeros(n, dtype=np.int64)
    rolled = np.zeros(n, dtype=np.int64)
    off_route = np.zeros(n, dtype=np.int64)
    for person in PERSONS:
        amount = raw[f"{person}_current_amount"].to_numpy(dtype=np.int64)
        plan_type = raw[f"{person}_current_type"].to_numpy(dtype=np.int64)
        account = np.isin(plan_type, _CURRENT_ACCOUNT_TYPES[new])
        value, reported, dk, topped = _decoded(
            amount, AMOUNT_WIDTHS["current_amount"]
        )
        current += np.where(account, value, 0)
        items += account & reported
        unreported += account & dk
        top += account & topped
        off_route += ~account & (amount != 0)
        for plan in PREVIOUS_PLANS:
            plan_type = raw[f"{person}_prev{plan}_type"].to_numpy(
                dtype=np.int64
            )
            for part in ("combo", "dc"):
                stem = f"{person}_prev{plan}_{part}"
                disposition = raw[f"{stem}_disposition"].to_numpy(
                    dtype=np.int64
                )
                amount = raw[f"{stem}_amount"].to_numpy(dtype=np.int64)
                value, reported, dk, topped = _decoded(
                    amount, AMOUNT_WIDTHS[f"{part}_amount"]
                )
                route = _account_route(part, plan_type, wave)
                left = disposition == COUNTED_DISPOSITION
                counted = route & left
                previous += np.where(counted, value, 0)
                items += counted & reported
                unreported += counted & dk
                top += counted & topped
                rolled += route & (disposition == EXCLUDED_IRA_DISPOSITION)
                off_route += ~route & left & (amount != 0)
    values = {
        "employer_dc": current + previous,
        "employer_dc_current": current,
        "employer_dc_previous": previous,
        "employer_dc_items": items,
        "employer_dc_unreported": unreported,
        "employer_dc_top_coded": top,
        "employer_dc_ira_rollover_items": rolled,
        "employer_dc_off_route_items": off_route,
    }
    out = raw.copy()
    for column in BALANCE_COLUMNS:
        out[column] = values[column]
    return out


def _verify_labels(
    labels: Mapping[str, str], table: Mapping[str, tuple[str, str]], wave: int
) -> None:
    by_label: dict[str, list[str]] = {}
    for name, label in labels.items():
        by_label.setdefault(" ".join(str(label).split()), []).append(name)
    for concept, (var, label) in table.items():
        family._verified(dict(labels), var, label, wave)
        holders = sorted(by_label.get(" ".join(label.split()), []))
        if holders != [var]:
            raise ValueError(
                f"family {wave}: label {label!r} ({concept}) is carried by "
                f"{holders}; expected only {var}. The release layout may "
                "have changed."
            )


def _verify_widths(sps_path: Path, wave: int) -> None:
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    for concept, (var, _) in _VARS[wave].items():
        kind = _kind(concept)
        want = AMOUNT_WIDTHS.get(kind, 1)
        width = int(layout.loc[var, "end"]) - int(layout.loc[var, "start"])
        if width + 1 != want:
            raise ValueError(
                f"family {wave}: {var} ({concept}) is {width + 1} "
                f"characters wide; the adjudicated width is {want}"
            )


def read_employer_dc(
    wave: int,
    *,
    data_dir: Path | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read one wave's label-verified P-section items and U7 balances.

    One row per responding family with ``wave``, ``interview``, every
    concept of :func:`employer_dc_variables` as recorded and the columns
    of :data:`BALANCE_COLUMNS` (:func:`employer_dc_balances`).  Labels,
    field widths and code domains are verified; an undocumented code is
    refused.
    """

    wave = int(wave)
    table = employer_dc_variables(wave)
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    _verify_labels(labels, table, wave)
    _verify_widths(sps_path, wave)
    raw = family_income._read_columns(
        sps_path, txt_path, [var for var, _ in table.values()], nrows
    )
    frame = pd.DataFrame(
        {concept: raw[var] for concept, (var, _) in table.items()}
    )
    context = f"family {wave} employer DC"
    _check_codes(frame, wave, context)
    if frame["interview"].duplicated().any():
        raise ValueError(f"{context}: duplicate interview numbers")
    frame = employer_dc_balances(frame, wave)
    frame.insert(0, "wave", wave)
    return frame.reset_index(drop=True)


def reconcile_employer_dc(frame: pd.DataFrame, wave: int) -> dict[str, int]:
    """Counts of P-section records against the questionnaires' routing.

    Nonzero amounts (actual, top-coded, DK or refused) by where the
    questionnaires route them: a current-job amount whose plan type (P16,
    P86) has no account; a "both" amount (P49, P119) whose plan type is
    not "both" or whose disposition is neither rolled over nor left to
    accumulate; an account amount (P65, P135) whose disposition is
    neither, and the account amounts by plan type: DC, formula and DK
    (U7's route) and "both" (a re-ask U7 does not take), NA and Inap.
    (off every route).  Also the number of previous plans that carry both
    a "both" amount and an account amount.  Then the families by what U7
    finds.  Counts only.
    """

    wave = int(wave)
    new = _new_codes(wave)
    asked = (EXCLUDED_IRA_DISPOSITION, COUNTED_DISPOSITION)
    out: dict[str, int] = {
        "n_families": int(len(frame)),
        "current_amount_without_account_plan": 0,
        "combo_amount_off_route": 0,
        "dc_amount_disposition_off_route": 0,
        "dc_amount_plan_type_account": 0,
        "dc_amount_plan_type_dk": 0,
        "dc_amount_plan_type_formula": 0,
        "dc_amount_plan_type_both": 0,
        "dc_amount_plan_type_na": 0,
        "dc_amount_plan_type_inap": 0,
        "plans_with_combo_and_dc_amounts": 0,
    }
    for person in PERSONS:
        amount = frame[f"{person}_current_amount"]
        kind = frame[f"{person}_current_type"]
        out["current_amount_without_account_plan"] += int(
            ((amount != 0) & ~kind.isin(_CURRENT_ACCOUNT_TYPES[new])).sum()
        )
        for plan in PREVIOUS_PLANS:
            plan_type = frame[f"{person}_prev{plan}_type"]
            stem = f"{person}_prev{plan}"
            combo = frame[f"{stem}_combo_amount"] != 0
            out["combo_amount_off_route"] += int(
                (
                    combo
                    & (
                        (plan_type != _PREVIOUS_BOTH_TYPE[new])
                        | ~frame[f"{stem}_combo_disposition"].isin(asked)
                    )
                ).sum()
            )
            dc = frame[f"{stem}_dc_amount"] != 0
            out["dc_amount_disposition_off_route"] += int(
                (dc & ~frame[f"{stem}_dc_disposition"].isin(asked)).sum()
            )
            out["plans_with_combo_and_dc_amounts"] += int((combo & dc).sum())
            for key, codes in (
                ("account", (_PREVIOUS_ACCOUNT_TYPE[new],)),
                ("dk", (PREVIOUS_DK_TYPE,)),
                ("formula", (PREVIOUS_FORMULA_TYPE,)),
                ("both", (_PREVIOUS_BOTH_TYPE[new],)),
                ("na", (9,)),
                ("inap", (0,)),
            ):
                out[f"dc_amount_plan_type_{key}"] += int(
                    (dc & plan_type.isin(codes)).sum()
                )
    for column, key in (
        ("employer_dc", "families_employer_dc_positive"),
        ("employer_dc_current", "families_current_positive"),
        ("employer_dc_previous", "families_previous_positive"),
    ):
        out[key] = int((frame[column] > 0).sum())
    for column, key in (
        ("employer_dc_unreported", "families_with_unreported_amount"),
        ("employer_dc_top_coded", "families_with_top_coded_amount"),
        (
            "employer_dc_ira_rollover_items",
            "families_with_ira_rollover_excluded",
        ),
        ("employer_dc_off_route_items", "families_with_off_route_amount"),
    ):
        out[key] = int((frame[column] > 0).sum())
    return out
