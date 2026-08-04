#!/usr/bin/env python3
"""Author the candidate-free source review for R_Q document 54.

Document 54 is the 1995 PSID ``QUESTION BY QUESTION OBJECTIVES`` manual.  It
is interviewer-objective prose about the 1995 family questionnaire rather than
the questionnaire form itself, so every retained occurrence is an exact printed
atom of the covered-earnings architecture that the manual describes.

The helper encodes the completed whole-document review as reviewer-approved
source windows, hand-specified complete source atoms, and exact UTF-8 spans.
It never opens the stage-1 candidate artifact.  Direct lexical detection is
used only for the lexeme-granular anchor kinds inside the source regions that
survived semantic review; the annotation builder joins the resulting sealed
review to candidates afterwards.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import build_rq_stage2_document_054_annotation as annotation

ROOT = Path(__file__).resolve().parents[1]

# Lexeme-granular anchor kinds keep their independently re-derived span because
# the printed atom is exactly one token or noun phrase.  The other five kinds
# are physical-line detections whose spans truncate the printed source clause,
# so every retained row of those kinds is hand-specified below.
DETECTED_KINDS = frozenset(
    {
        "role_anchor",
        "job_anchor",
        "remuneration_component_anchor",
        "farm_aggregate_anchor",
        "business_aggregate_anchor",
    }
)
HANDS = "field_purpose_prompt"
FLOW = "flow_branch_label"
CTX = "context_anchor"
ALIAS = "repeat_or_alias_instruction"
TOTAL = "role_total_anchor"

# (page, kind, opening literal, closing literal or None, nth, close_nth).
# Every entry was read off the exact page bytes during the whole-page pass.
MANUAL_ATOMS: tuple[tuple[Any, ...], ...] = (
    # -- page 9: Section B scope, the B1-B3 employment-status gate ----------
    (
        9,
        FLOW,
        "SECTIONS BAND C APPLY TO THE CURRENT HEAD OF THE FU EVEN IF",
        "YOUR RESPONDENT IS NOT THE HEAD.",
        1,
        1,
    ),
    (
        9,
        HANDS,
        "Bl-3   It is crucial that you get an accurate reply to Bl-B3",
        "ask Section B or skip to Section C.",
        1,
        1,
    ),
    (9, HANDS, "Mark as many choices as the R mentions at Bl.", None, 1, 1),
    (9, FLOW, "If R's answer include 1.", "with Section B.", 1, 1),
    (
        9,
        FLOW,
        "If only CODES 3-8 are checked and B3 is YES",
        "continue with Section B;",
        1,
        1,
    ),
    (9, FLOW, "if B3 is NO, GO TO Section C.", None, 1, 1),
    (
        9,
        ALIAS,
        "All the instructions for Sections B and C will crop up again in Sections D and E",
        "so be sure ou are familiar with them.",
        1,
        1,
    ),
    (9, CTX, "WORKING NOW", None, 1, 1),
    (9, CTX, "TEMPORARILY OFF from work", None, 1, 1),
    (9, CTX, "WORKING NOW", None, 2, 1),
    (9, CTX, "ONLY TEMPORARILY LAID OFF", None, 1, 1),
    (9, CTX, "LOOKING FOR WORK, UNEMPLOYED", None, 1, 1),
    (9, CTX, "NOT WORKING/NOT LOOKING", None, 1, 1),
    (9, CTX, "temporarily laid off or is on strike", None, 1, 1),
    (9, CTX, "retired people", None, 1, 1),
    # -- page 10: main vs extra job rule, B4/B5 self-employment, B8, B9 -----
    (
        10,
        ALIAS,
        "Note: B4-B59 refer to Head's main job or consecutive main jobs.",
        None,
        1,
        1,
    ),
    (10, FLOW, "When R", "Head spends the most hrs/wk.", 1, 1),
    (10, FLOW, "If Head spends an equal amount of time on", "main job.", 1, 1),
    (
        10,
        ALIAS,
        "For more information on main vs. extra jobs, see B82 Q-x-Qs.",
        None,
        1,
        1,
    ),
    (
        10,
        HANDS,
        "B4.      Be careful with the following situations",
        "marginal notes:",
        1,
        1,
    ),
    (10, FLOW, "Incorporated family farm", "SELF-employed.", 1, 1),
    (10, FLOW, "If they can't, record", "ask B4a and give us details.", 1, 1),
    (
        10,
        ALIAS,
        "Similarly, any other case in which employment by others",
        "B9-Bll.",
        1,
        1,
    ),
    (
        10,
        HANDS,
        "B5.      Many self-employed people and professionals",
        "don't think B5 applies to them.",
        1,
        1,
    ),
    (
        10,
        FLOW,
        "If R is very clear that some other category applies (e.g., partnership),",
        "note it in a marginal note.",
        1,
        1,
    ),
    (
        10,
        HANDS,
        "B8.      We are not asking whether R belongs to any labor unions",
        "her/his current main job.",
        1,
        1,
    ),
    (
        10,
        ALIAS,
        "Remember:            For Spanish language interviews",
        "end for ou to translate.",
        1,
        1,
    ),
    (
        10,
        HANDS,
        "B9-9a.   Follow the guidelines below",
        "job duties/activities.",
        1,
        1,
    ),
    (10, CTX, "hrs/wk", None, 1, 1),
    (10, CTX, "labor unions", None, 1, 1),
    (10, CTX, "occupation and industry", None, 1, 1),
    # -- page 11: occupation and industry probes ---------------------------
    (
        10,
        HANDS,
        "1.         Probe for clear complete answers.",
        "distinguish among",
        1,
        1,
    ),
    (
        11,
        FLOW,
        "If Head is a road construction worker",
        "he or she provides labor only.",
        1,
        1,
    ),
    (
        11,
        HANDS,
        "5.          Particularly unacceptable answers are:",
        "sufficient information.",
        1,
        1,
    ),
    (
        11,
        FLOW,
        "If Head works both for him/herself and for someone",
        "selling insurance, real estate).",
        1,
        1,
    ),
    (
        11,
        HANDS,
        "BlO.   The type of business or industry is fit into an industrial code",
        "whether a sales",
        1,
        1,
    ),
    (
        11,
        HANDS,
        "The following list of questions should help you know what probes to use",
        "information about occupation and industry.",
        1,
        1,
    ),
    (
        11,
        FLOW,
        "3.          If Head is employed by the government",
        "federal, state or local.",
        1,
        1,
    ),
    (11, CTX, "industry", None, 1, 1),
    (11, CTX, "occupation and industry", None, 1, 1),
    (11, CTX, "employed by the government", None, 1, 1),
    # -- page 12: industry probe list; armed-forces main job ---------------
    (
        12,
        ALIAS,
        '7.    "Machinist" is a specialized occupation',
        "use the terms interchangeably .",
        1,
        1,
    ),
    (
        12,
        FLOW,
        "16.   When Head's main job is in the Armed Forces",
        "commissioned, non-commissioned or enlisted.",
        1,
        1,
    ),
    (
        12,
        FLOW,
        "22.   If occupation is manager or supervisor",
        "sales? data processing? etc.",
        1,
        1,
    ),
    (12, CTX, "Armed Forces", None, 1, 1),
    # -- page 13: B11 employer name; B12-B19 pay rates ---------------------
    (
        13,
        HANDS,
        "B11.     You will be asking employer's name for every employer",
        "for referencing in succeeding questions.",
        1,
        1,
    ),
    (
        13,
        FLOW,
        "If the R does not give you an",
        "in succeeding questions.",
        1,
        1,
    ),
    (
        13,
        ALIAS,
        "use the information at B9-10 to construct a short job name or title",
        None,
        1,
        1,
    ),
    (
        13,
        HANDS,
        "B12-19. Questions B12, B13, B16, and B18 refer to Head's regular pay.",
        "be sure to check the appropriate time period for the amount given.",
        1,
        1,
    ),
    (
        13,
        HANDS,
        "B12.     The OTHER category is for everything that is not salary",
        "select from the B18 choices.",
        1,
        1,
    ),
    (
        13,
        FLOW,
        "B14.     This should be NO if Head's income is a fixed",
        "the reply should be",
        1,
        1,
    ),
    (
        13,
        HANDS,
        "B15.     Select all that R mentions.",
        "half-time, shift differentials, etc.",
        1,
        1,
    ),
    (
        13,
        HANDS,
        "B19.     We know that B19 may be difficult for some situations",
        "try to get an estimate from",
        1,
        1,
    ),
    (
        13,
        HANDS,
        "B17.     Select all that R mentions.",
        "half-time, shift differentials, etc.",
        1,
        1,
    ),
    (
        13,
        HANDS,
        'B20.     "Another job" can mean a different position',
        "to something else.",
        1,
        1,
    ),
    (13, CTX, "regular pay", None, 1, 1),
    (13, CTX, "overtime or extra hours", None, 1, 1),
    (13, CTX, "hourly", None, 1, 1),
    (13, CTX, "regular hours", None, 1, 1),
    (13, CTX, "regular work time", None, 1, 1),
    # -- page 14: B21-B30, work-history frame ------------------------------
    (
        14,
        HANDS,
        "B21.     Select all that apply and specify at 7. OTHER",
        "the given",
        1,
        1,
    ),
    (14, FLOW, 'If R says "looked at newspaper', "at 7. OTHER.", 1, 1),
    (
        14,
        HANDS,
        "B23.     By employer, we mean company, firm, or organization",
        "not a specific boss.",
        1,
        1,
    ),
    (14, ALIAS, "if Head worked", 'give us the total "altogether."', 1, 1),
    (
        14,
        HANDS,
        "With questions B24-B59 and pink Work History Supplements",
        "spells of employment during 1994.",
        1,
        1,
    ),
    (
        14,
        HANDS,
        "A quick definition of main vs. extra jobs:",
        "a complete account of work with each employer.",
        1,
        1,
    ),
    (
        14,
        HANDS,
        "B24.     Both B23 and B24 refer to the present employer.",
        "or self-employment).",
        1,
        1,
    ),
    (
        14,
        FLOW,
        'The "Other Year" category is only to be used',
        "of 1993 or earlier.",
        1,
        1,
    ),
    (
        14,
        FLOW,
        "B25-29 . For Heads who began their present employment in 1994",
        "in the 7 OTHER",
        1,
        1,
    ),
    (
        14,
        FLOW,
        "B30.     For Heads who began their present employment in 1995",
        "any 1994 main job employers.",
        1,
        1,
    ),
    (
        14,
        TOTAL,
        "While B23 asks for the total amount of",
        "worked for this employer",
        1,
        1,
    ),
    (
        14,
        CTX,
        "changes in employer and changes in position with the same",
        None,
        1,
        1,
    ),
    (14, CTX, "spells of employment", None, 1, 1),
    # -- page 15: B31-B45a, main/extra overlap rules -----------------------
    (
        15,
        FLOW,
        "B31-34. For Heads who began their present employment prior to 1994",
        "if any .",
        1,
        1,
    ),
    (
        15,
        ALIAS,
        "B35-36 . See B9-B9a for probes and cautions in asking occupation details.",
        None,
        1,
        1,
    ),
    (
        15,
        HANDS,
        "B38.       The amount at B38 should be an average",
        "with the",
        1,
        1,
    ),
    (
        15,
        HANDS,
        "B39.       Mark the months of 1994 that Head worked",
        "vacation, leave, temporary layoff, sick time, etc.",
        1,
        1,
    ),
    (
        15,
        FLOW,
        "If Head worked part of the year for this employer",
        "about them.",
        1,
        1,
    ),
    (15, FLOW, 'B40.       If B40 is "NO"', "skip to B60.", 1, 1),
    (
        15,
        FLOW,
        "If Head started with her/his present employer before 1994",
        "Main vs. Extra job.",
        1,
        1,
    ),
    (
        15,
        FLOW,
        "If Head started with his/her present employer in 1994",
        "through B41-B42d.",
        1,
        1,
    ),
    (
        15,
        FLOW,
        "If Head's most recent start with present employer was in 1995",
        "with his/her present employer.",
        1,
        1,
    ),
    (
        15,
        ALIAS,
        "B41-41c See B9-Bll instructions .",
        "after the interview.",
        1,
        1,
    ),
    (15, ALIAS, "B42.       See B39.", "main vs. extra job.", 1, 1),
    (
        15,
        FLOW,
        "If there is a partial overlap of 2-11 months",
        "about the overlap.",
        1,
        1,
    ),
    (
        15,
        FLOW,
        "If there is a complete overlap of all 12 months",
        "(B82-106).",
        1,
        1,
    ),
    (15, ALIAS, "B43-44.                See B4-B5 instructions.", None, 1, 1),
    (15, CTX, "months of 1994", None, 1, 1),
    (15, CTX, "at least one day", None, 1, 1),
    # -- page 16: B45b-B59, Work History Supplement ------------------------
    (16, ALIAS, "B45b.                See B38 instructions.", None, 1, 1),
    (
        16,
        ALIAS,
        "B46-B47.             Again we're looking for the most recent position change in 1994.",
        "regarding detailing the position change.",
        1,
        1,
    ),
    (
        16,
        FLOW,
        "Also, be careful of Head changing from main job to extra job.",
        "employment.",
        1,
        1,
    ),
    (16, ALIAS, "B49-49a.             See B9-9a instructions.", None, 1, 1),
    (16, ALIAS, "B52.                 See B38 instructions.", None, 1, 1),
    (
        16,
        FLOW,
        "B53-55.              Since Head is currently employed on a different main job",
        "(B82-B106).",
        1,
        1,
    ),
    (16, ALIAS, "B57a.                See B38 instructions.", None, 1, 1),
    (
        16,
        FLOW,
        "B59.                 If Head had any other main-job employers during 1994",
        "go to B60.",
        1,
        1,
    ),
    (
        16,
        HANDS,
        "The questionnaire employment sections are designed to cover the two most recent main job",
        "for each additional employer.",
        1,
        1,
    ),
    (16, FLOW, "Use as many", "since January 1, 1994.", 1, 1),
    (16, CTX, "up to four main jobs and up to four extra jobs", None, 1, 1),
    (16, CTX, "four job loops", None, 1, 1),
    # -- page 17: Work History Supplement item cross-references ------------
    (
        17,
        ALIAS,
        "S41-41c.    See B9-Bll instructions.",
        "after the interview.",
        1,
        1,
    ),
    (17, ALIAS, "S42.        See B39 instructions.", None, 1, 1),
    (17, ALIAS, "S42a-42d.   See B42a-42d instructions.", None, 1, 1),
    (17, ALIAS, "S43-44.     See B4-B5 instructions.", None, 1, 1),
    (17, ALIAS, "S45b.       See B38 instructions.", None, 1, 1),
    (17, ALIAS, "S46-47.     See B25-B29 instructions.", "for the most", 1, 1),
    (17, ALIAS, "S49-49a.    See B9-B9a instructions.", None, 1, 1),
    (17, ALIAS, "S52.        See B38 instruction.", None, 1, 1),
    (17, ALIAS, "S53-55.     See B53-B55 instructions.", None, 1, 1),
    (17, ALIAS, "S57a.       See B38 instructions.", None, 1, 1),
    (
        17,
        FLOW,
        "S59.        Complete one WHS for each additional employer",
        "questionnaire.",
        1,
        1,
    ),
    # -- page 18: 1994 work weeks frame ------------------------------------
    (
        18,
        FLOW,
        "NOTE: ASK B60-78 FOR ALL HEADS!",
        "Not Looking for a job (B75-B77a)",
        1,
        1,
    ),
    (
        18,
        HANDS,
        "The objectives of this sequence are:",
        "3 . Annual overtime hours",
        1,
        1,
    ),
    (
        18,
        HANDS,
        "Work in these questions means simply and only main job employment.",
        "expected to return to the",
        1,
        1,
    ),
    (18, CTX, "Employed but temporarily off the job", None, 1, 1),
    (18, CTX, "Unemployed and looking for work", None, 1, 1),
    (18, CTX, "Not Employed and Not Looking for a job", None, 1, 1),
    (18, CTX, "all 52 weeks of 1994", None, 1, 1),
    (18, CTX, "Average work hours per week for weeks worked", None, 1, 1),
    (18, CTX, "Annual overtime hours", None, 1, 1),
    (18, CTX, "Temporary Layoff", None, 2, 1),
    # -- page 19: unemployed / not-looking definitions ---------------------
    (
        19,
        HANDS,
        "Weeks spent as unemployed weeks require two conditions.",
        "no probing).",
        1,
        1,
    ),
    (
        19,
        HANDS,
        "Not Workin~ and Not Lookin~ is often confused",
        "employed at the time.",
        1,
        1,
    ),
    (
        19,
        FLOW,
        "Head must have been employed and missed time from his or her job",
        "recorded at B75-B77a.",
        1,
        1,
    ),
    (
        19,
        ALIAS,
        "B72-74. Check dates at B74 against work history",
        "on the screen).",
        1,
        1,
    ),
    (19, CTX, "unemployed weeks", None, 1, 1),
    (19, CTX, "Not Workin~ and Not Lookin~", None, 1, 1),
    (19, CTX, "temporarily laid off", None, 2, 1),
    # -- page 20: B75-B81d hours and overtime ------------------------------
    (
        20,
        ALIAS,
        "B75-77. Again, check these dates against the work history",
        "and WHSs.",
        1,
        1,
    ),
    (
        20,
        HANDS,
        "B78.     We want the total number of weeks during which Head did any work.",
        "combine hours from different weeks",
        1,
        1,
    ),
    (
        20,
        TOTAL,
        "We want the total number of weeks during which Head did any work.",
        None,
        1,
        1,
    ),
    (
        20,
        HANDS,
        "B79.     This is the average hours per week on main job(s) worked in 1994.",
        None,
        1,
        1,
    ),
    (
        20,
        HANDS,
        "B80-81. Be careful not to double count any overtime hours",
        "hours in 1994.",
        1,
        1,
    ),
    (
        20,
        FLOW,
        "B81a-d. If Head worked more than one main job in 1994",
        "overtime hours for each job.",
        1,
        1,
    ),
    (
        20,
        HANDS,
        "B82.     Main vs. Extra Job distinctions are not as difficult as they seem.",
        "during the same time period.",
        1,
        1,
    ),
    (
        20,
        FLOW,
        "But if Head was working for money at all during these times",
        "considered a main job.",
        1,
        1,
    ),
    (20, CTX, "average hours per week", None, 1, 1),
    (20, CTX, "average", None, 3, 1),
    (20, CTX, "paid and unpaid overtime", None, 1, 1),
    # -- page 21: B83-B105 extra jobs --------------------------------------
    (21, HANDS, "work and income for Head.", None, 1, 1),
    (21, HANDS, "we need to know", "during the past year.", 1, 1),
    (
        21,
        ALIAS,
        "B83-85. Follow the same general rules that you used for probing on B9-B11.",
        None,
        1,
        1,
    ),
    (21, ALIAS, "B86.     See Bll QxQ.", None, 1, 1),
    (
        21,
        HANDS,
        "B87.     Be sure to record the unit of time for the amount given.",
        "this is net income.",
        1,
        1,
    ),
    (
        21,
        HANDS,
        "B88.     This is the number of calendar weeks in 1994",
        "on this",
        1,
        1,
    ),
    (
        21,
        HANDS,
        "B89.     This is average hours per week for the weeks Head worked an extra job.",
        "for that job during 1994.",
        1,
        1,
    ),
    (
        21,
        ALIAS,
        "The sequence on pp. 24-25 (B94-B105) is a repeat of B82-B93 and is",
        "not duplicated here.",
        1,
        1,
    ),
    (21, CTX, "calendar weeks in 1994", None, 1, 1),
    (21, CTX, "average hours per week", None, 1, 1),
    (21, CTX, "total number of hours", None, 1, 1),
    # -- page 22: Section C ------------------------------------------------
    (
        22,
        HANDS,
        "Section C parallels Section B quite closely",
        "apply here, too.",
        1,
        1,
    ),
    (
        22,
        FLOW,
        "If Head has done any work since January L. 1994,",
        "work history for 1994.",
        1,
        1,
    ),
    (
        22,
        ALIAS,
        "Note that, as at B24, we have provided",
        '"Don\'t Know".',
        1,
        1,
    ),
    (22, FLOW, "Continue with C9-C51 and WHS as necessary.", None, 1, 1),
    (
        22,
        ALIAS,
        "See the comparable questions/instructions from Section B.",
        None,
        1,
        1,
    ),
    (
        22,
        ALIAS,
        "C9-ll.   Probe for detail, as in the occupation/industry instructions at B9-B11.",
        "after the Interview.",
        1,
        1,
    ),
    (22, ALIAS, "C12-14. For instructions, see B4-B5.", None, 1, 1),
    (22, ALIAS, "C14a.    See Bll instructions.", None, 1, 1),
    (22, ALIAS, "C15.     See B55 instructions.", None, 1, 1),
    (
        22,
        ALIAS,
        "C16-51. This sequence, with WORK HISTORY SUPPLEMENTS if needed",
        "confusing situations.",
        1,
        1,
    ),
    (
        22,
        ALIAS,
        "C52-98. We have not reproduced the remainder of Section C questionnaire pages here.",
        "they parallel B60-B 106.",
        1,
        1,
    ),
    (22, CTX, "work week information", None, 1, 1),
    # -- page 23: Sections D and E ------------------------------------------
    (
        23,
        HANDS,
        'Review the definitions of Head, Wife, and "Wife."',
        'Do not use the terms wife or\n"WIFE".',
        1,
        1,
    ),
    (
        23,
        ALIAS,
        'Sections D and E apply to current Wife or "Wife" only.',
        "except for",
        1,
        1,
    ),
    (
        23,
        ALIAS,
        "Question objectives and concepts forB and C apply to D and E.",
        None,
        1,
        1,
    ),
    (
        23,
        FLOW,
        "Dl-la.    The D1 checkpoint routes all Female Heads and Male Heads",
        "through to Section F.",
        1,
        1,
    ),
    (
        23,
        ALIAS,
        "We have not reproduced the remainder of Sections D and E",
        "Sections B and C QxQs.",
        1,
        1,
    ),
    # -- page 24: F2-3 routes income-producing work back to B/C and D/E ----
    (
        24,
        ALIAS,
        "That housework is income-producing",
        'for the\n         Wife/"Wife").',
        1,
        1,
    ),
    (24, CTX, 'time spent by Head or Wife/"Wife" cleaning', None, 1, 1),
    # -- page 26: Section G frame and farm receipts/expenses ---------------
    (
        26,
        FLOW,
        'If Head or Wifei"Wife" reports work income in Section G',
        "in Section BIC or DIE.",
        1,
        1,
    ),
    (
        26,
        FLOW,
        'If Head or Wifei"Wife" reports working during 1994 in the employment sections',
        "must be reported in Section G.",
        1,
        1,
    ),
    (
        26,
        HANDS,
        "All wages and salaries listed in Section G should be before taxes and other deductions.",
        "but before income taxes.",
        1,
        1,
    ),
    (
        26,
        ALIAS,
        "G1a.    You will know from B9b and B10 whether Head's current occupation is farmer or",
        '"income\n        included at G4. "',
        1,
        1,
    ),
    (
        26,
        HANDS,
        "G2.     Receipts from normal farm operations include:",
        "crop loans (not considered income).",
        1,
        1,
    ),
    (
        26,
        HANDS,
        "G3.     Farm operating expenses can include:",
        "property taxes (but not federal income taxes).",
        1,
        1,
    ),
    (26, CTX, "work hours", None, 1, 1),
    (26, CTX, "her\n        work hours in Section DIE", None, 1, 1),
    # -- page 27: G4 farm income; G5-G11c business income ------------------
    (
        27,
        TOTAL,
        "G4.        Farm income equals total receipts (see G2) minus operating expenses (see G3).",
        None,
        1,
        1,
    ),
    (
        27,
        FLOW,
        "WE MUST HAVE WORK HOURS FOR ALL INCOME FROM A JOB AND",
        "SENDING THE COMPLETED INTERVIEW IN.",
        1,
        1,
    ),
    (
        27,
        HANDS,
        "G5-7a.     Do not include stock ownership in G5.",
        "specify who\n           in the family owned it.",
        1,
        1,
    ),
    (
        27,
        FLOW,
        "If the family had more than one business, repeat questions",
        "for each separate business up to 5.",
        1,
        1,
    ),
    (
        27,
        FLOW,
        'Many self-employed people are not set up as a "business"',
        "G18-G20c) .",
        1,
        1,
    ),
    (
        27,
        HANDS,
        "G9a-G9d.                 These questions are crucial.",
        "in the G76-G81 and G95-G97 sequences.",
        1,
        1,
    ),
    (
        27,
        HANDS,
        "G 11a.     The amount given here is net profit",
        "do not double count the draw.",
        1,
        1,
    ),
    (
        27,
        FLOW,
        'If the Wife/"Wife" or other FU member is not f! part owner',
        "which FU members received it.",
        1,
        1,
    ),
    (
        27,
        ALIAS,
        "G11c.      Attach an extra page or pages to record information for each additional business.",
        None,
        1,
        1,
    ),
    (27, CTX, "work time", None, 1, 1),
    (
        27,
        CTX,
        "these hours should\n                         be reported in Section B/C",
        None,
        1,
        1,
    ),
    # -- page 28: G12-G18b Head labour income ------------------------------
    (
        28,
        FLOW,
        "G12.         If Head was working in 1994",
        'should be marked "YES".',
        1,
        1,
    ),
    (
        28,
        ALIAS,
        "Respondents sometimes give an answer of NO here thinking",
        "this question asks about last year's earnings.",
        1,
        1,
    ),
    (
        28,
        HANDS,
        "G13.         This question applies only to current Head.",
        "Be careful of the following:",
        1,
        1,
    ),
    (28, HANDS, "fixed salary rates:", "not the current salary rate.", 1, 1),
    (
        28,
        HANDS,
        "complicated work history:",
        "total income from all 1994 wages.",
        1,
        1,
    ),
    (28, FLOW, "self-employed Heads:", "should be listed here.", 1, 1),
    (
        28,
        FLOW,
        "If an amount is given for both G lla and G 13",
        "the\n             same money recorded twice here.",
        1,
        1,
    ),
    (
        28,
        FLOW,
        'G14.         Note the phrase "in addition to this."',
        "do not double-count jj;.",
        1,
        1,
    ),
    (
        28,
        FLOW,
        "G16.         If earnings are solely from bonuses, overtime, tips or commissions",
        "select YES here.",
        1,
        1,
    ),
    (
        28,
        FLOW,
        "G 17e.       If there are no work hours reported in Section B or C",
        "will automatically be asked.",
        1,
        1,
    ),
    (
        28,
        HANDS,
        "G18.         PROFESSIONAL PRACTICE:",
        "We need net income but after expenses.",
        1,
        1,
    ),
    (
        28,
        FLOW,
        "G18b.        FARMING or MARKET GARDENING:",
        "farming in 1994 (main or extra jobs).",
        1,
        1,
    ),
    (28, TOTAL, "We want total 1994\n               wages/salary", None, 1, 1),
    (28, TOTAL, "get total income from all 1994 wages.", None, 1, 1),
    (28, CTX, "work hours", None, 1, 1),
    # -- page 29: G18c roomers/boarders; G19-G24 units and extra jobs ------
    (29, HANDS, "G18c.    ROOMERS OR BOARDERS:", "in G25a.", 1, 1),
    (
        29,
        FLOW,
        "Head must do work for this money",
        "work hours should be mentioned in Section B/C.",
        1,
        1,
    ),
    (
        29,
        HANDS,
        "G 19a-c. It is very important to select the appropriate unit of time",
        "for all possible types of income.",
        1,
        1,
    ),
    (
        29,
        HANDS,
        "G20a-c. We want to know during which months of 1994 this income was received.",
        "for each type of income received.",
        1,
        1,
    ),
    (
        29,
        ALIAS,
        "G21a-c. Again, make sure you have work hours in Section B/C",
        "automatically is asked.",
        1,
        1,
    ),
    (
        29,
        HANDS,
        "G22-24. The purpose of this sequence is to help you make sure",
        "we get the income from them.",
        1,
        1,
    ),
    (29, CTX, "months of 1994", None, 1, 1),
    (29, CTX, "work hours", None, 2, 1),
    # -- page 30: G25b boundary between incorporated business and dividends
    (
        30,
        FLOW,
        "If Head owns a small incorporated business",
        "belong here.",
        1,
        1,
    ),
    # -- page 34: G50-G52b Wife's work income; Job Supplement --------------
    (
        34,
        ALIAS,
        "G50-52 . Remember that work hours in Section DIE imply income here and vice versa.",
        "tips, commissions\n         or bonuses.",
        1,
        1,
    ),
    (
        34,
        FLOW,
        "If some or all of the Wife's/\"Wife's\" income is from work in a business",
        'should be "before any taxes or deductions".',
        1,
        1,
    ),
    (
        34,
        FLOW,
        "G52b .     Again, if income is reported but no work hours were recorded",
        "will automatically be asked.",
        1,
        1,
    ),
    (
        34,
        TOTAL,
        "Make sure\n         Wife's/\"Wife's\" income from all work sources is recorded",
        None,
        1,
        1,
    ),
    (34, CTX, "work hours in Section DIE", None, 1, 1),
    # -- page 35: Job Supplement GJ0a-GJ11 ---------------------------------
    (
        35,
        HANDS,
        "section where this could occur; each has a checkpoint or question",
        "the correct question sequence in these cases.",
        1,
        1,
    ),
    (
        35,
        FLOW,
        "GJOa-b. Indicate which of seven places you discovered the missing job information:",
        "G52b Wife's/\"WIFE'S\" WAGE/SALARY Income",
        1,
        1,
    ),
    (
        35,
        ALIAS,
        "GJ3-3a.     Follow the same general rules that you used for probing on B9-B11.",
        "help us get the details.",
        1,
        1,
    ),
    (
        35,
        FLOW,
        "GJ3ab.      If it was work hours for business income (G9b or G9d)",
        "ask GJ3b then GJ4.",
        1,
        1,
    ),
    (
        35,
        HANDS,
        "GJ4.        This is the number of calendar weeks in 1994",
        "work on this job.",
        1,
        1,
    ),
    (
        35,
        HANDS,
        "GJ5.       This is average hours per week for the weeks worked on this job.",
        "get an estimate of total number of hours for that",
        1,
        1,
    ),
    (
        35,
        HANDS,
        "GJlO.       We mention negative alternatives",
        "are welcome.",
        1,
        1,
    ),
    (35, CTX, "calendar weeks in 1994", None, 1, 1),
    (35, CTX, "average hours per week", None, 1, 1),
    (35, CTX, "total number of hours", None, 1, 1),
    # -- page 36: OFUM movers-out still owe 1994 income and jobs -----------
    (
        36,
        FLOW,
        "DO NOT CROSS OFF OFUMs IF THEY'VE MOVED OUT OR DIED",
        "still in the FU.",
        1,
        1,
    ),
    (
        36,
        FLOW,
        "If there is an eligible OFUM listed in G71",
        "Use one booklet for each additional OFUM.",
        1,
        1,
    ),
    # -- page 38: OFUM income and work booklet G75-G82 ---------------------
    (
        38,
        ALIAS,
        'G75.      Unlike the Head/Wife/"Wife" employment status questions B1 and D1a',
        "definitions of employment status.)",
        1,
        1,
    ),
    (
        38,
        HANDS,
        "G76-82. If this person's employment was irregular",
        "amount earned.",
        1,
        1,
    ),
    (
        38,
        HANDS,
        "G77.      We use occupation to help us assign missing income data",
        "post-interview edit.",
        1,
        1,
    ),
    (
        38,
        HANDS,
        "G78.      List total income from each job here.",
        "number of units.",
        1,
        1,
    ),
    (38, TOTAL, "G78.      List total income from each job here.", None, 1, 1),
    (
        38,
        HANDS,
        "G79.      This figure should be the number of weeks in which any work was done.",
        None,
        1,
        1,
    ),
    (38, ALIAS, "See instructions\n          for B78.", None, 1, 1),
    (
        38,
        FLOW,
        "G81.      If employment was irregular and R can't give hours per week",
        "at that job.",
        1,
        1,
    ),
    (38, ALIAS, "See instructions for B79.", None, 1, 1),
    (
        38,
        TOTAL,
        "We're after total hours (weeks x hours per week) and total\n        amount earned.",
        None,
        1,
        1,
    ),
    (38, CTX, "hours per week", None, 2, 1),
    # -- page 39: children's labour income ---------------------------------
    (
        39,
        HANDS,
        "G92-98. Note these questions are only about children",
        "Please provide detail for each amount.",
        1,
        1,
    ),
    (
        39,
        TOTAL,
        "We need enough detail to calculate total amount of each type of income and total",
        "work hours for each labor income.",
        1,
        1,
    ),
    (39, CTX, "work hours for each labor income", None, 1, 1),
    # -- page 66: K36-K45 training, work years, full-time -------------------
    (
        66,
        HANDS,
        "K36-41.   We want such training here as trade school",
        "for jobs.",
        1,
        1,
    ),
    (
        66,
        HANDS,
        "K44.      This means the number of years in which any work was done",
        "Count time in the armed\n          services as work years.",
        1,
        1,
    ),
    (
        66,
        HANDS,
        "K45.      Thirty-five hours or more per week is full-time.",
        None,
        1,
        1,
    ),
    (66, CTX, "number of years in which any work was done", None, 1, 1),
    (66, CTX, "Thirty-five hours or more per week is full-time", None, 1, 1),
    # -- page 67: L4-L12 New Head occupation history -----------------------
    (
        67,
        ALIAS,
        "L4-5.       Probe to get as clear a picture as possible of the occupation",
        "collection of occupation information).",
        1,
        1,
    ),
    (
        67,
        HANDS,
        "L6.         We are interested in the similarity of occupations the New Head has had.",
        "held a number of diverse professions?",
        1,
        1,
    ),
    (
        67,
        FLOW,
        "These occupations should include things",
        "in the labor force",
        1,
        1,
    ),
    (
        67,
        HANDS,
        "L11-12.     There are two key phrases here.",
        "with the same company does count.",
        1,
        1,
    ),
    (67, CTX, "full time", None, 1, 1),
    (67, CTX, "labor force", None, 1, 1),
)

# Lexeme detections inside a retained window that name no earnings field.
REVIEWED_FALSE: frozenset[tuple[int, str, str]] = frozenset(
    {
        # "9. Organizations: profit? nonprofit?" is an organisational form.
        (12, "remuneration_component_anchor", "profit"),
        # "Heavy equipment or heavy machinery: farm? construction?"
        (12, "farm_aggregate_anchor", "farm"),
        # "the type of oil business" is an industry probe.
        (12, "business_aggregate_anchor", "business"),
        # "the type of business or industry" heads the industry probe list.
        (11, "business_aggregate_anchor", "business"),
    }
)

# Repeat and cross-reference instructions whose target is an anchor printed in
# this same document.  Keys are the exact (start, end) span of the instruction;
# values name the canonical and alias anchors it binds, by exact span and kind.
# Every other repeat instruction points outside this shard (at questionnaire
# item numbers that live in document 55) and is preserved unresolved.
LOCAL_REPEAT_BINDINGS: dict[
    int,
    dict[tuple[int, int], dict[str, tuple[tuple[int, int, int, str], ...]]],
] = {}
RELATION_BY_PAGE: dict[int, dict[tuple[int, int], str]] = {}


def _review_id(
    source_document_id: str,
    page_texts: Sequence[str],
    page_number: int,
    start: int,
    end: int,
    kind: str,
) -> str:
    matched = page_texts[page_number - 1].encode("utf-8")[start:end]
    if not matched:
        raise ValueError("empty reviewer span")
    matched.decode("utf-8", errors="strict")
    return "rq-review-occurrence:" + annotation._canonical_digest(
        [
            source_document_id,
            page_number,
            start,
            end,
            kind,
            annotation._sha256(matched),
        ]
    )


def author_review() -> dict[str, Any]:
    replay, index = annotation._source_replay_and_index()
    document, _identity = annotation._document_identity(replay, index)
    page_texts = annotation._extract_page_texts(document, replay)
    source_document_id = document["source_document_id"]
    interview_wave = document["interview_waves"][0]
    page_bytes = [page_text.encode("utf-8") for page_text in page_texts]

    def page_size(page: int) -> int:
        return len(page_bytes[page - 1])

    def find(page: int, literal: str, nth: int = 1) -> int:
        raw = literal.encode("utf-8")
        haystack = page_bytes[page - 1]
        position = -1
        for _ in range(nth):
            position = haystack.find(raw, position + 1)
            if position < 0:
                raise ValueError(
                    f"literal not found on page {page} (#{nth}): {literal!r}"
                )
        return position

    def span(
        page: int,
        opening: str,
        closing: str | None = None,
        nth: int = 1,
        close_nth: int = 1,
    ) -> tuple[int, int]:
        start = find(page, opening, nth)
        if closing is None:
            return start, start + len(opening.encode("utf-8"))
        raw = closing.encode("utf-8")
        haystack = page_bytes[page - 1]
        position = start - 1
        for _ in range(close_nth):
            position = haystack.find(raw, position + 1)
            if position < 0:
                raise ValueError(
                    f"closing literal not found on page {page}: {closing!r}"
                )
        return start, position + len(raw)

    def trim_span(page: int, start: int, end: int) -> tuple[int, int]:
        raw = page_bytes[page - 1]
        while start < end and raw[start : start + 1] in b" \t\r\n":
            start += 1
        while end > start and raw[end - 1 : end] in b" \t\r\n":
            end -= 1
        if start >= end:
            raise ValueError(f"empty span after trimming: page={page}")
        return start, end

    def full_pages(
        *ranges: tuple[int, int],
    ) -> dict[int, tuple[tuple[int, int], ...]]:
        return {
            page: ((0, page_size(page)),)
            for first, last in ranges
            for page in range(first, last + 1)
        }

    # Every byte of every one of the 69 pages was read.  These are the only
    # regions in which the manual states the covered-earnings architecture:
    # roles, jobs, remuneration, farm and business aggregates, work contexts,
    # and the routing among them.  Pages omitted here were reviewed and sealed
    # with zero retained occurrences -- the face sheet, thumbnail sketch,
    # housing, food, transfer and asset income, health, both health-care burden
    # supplements, Medicare permission, marriage and child histories, and the
    # education supplement.  Those sections carry Head/Wife tokens and worklike
    # prose ("work-limiting health problems"; "farm laborers ... who get living
    # quarters as part of their pay") that names no earnings field.
    source_windows: dict[int, tuple[tuple[int, int], ...]] = {
        **full_pages((9, 23), (26, 29)),
        24: (span(24, "F2-3.", "included in the housework hours."),),
        30: (
            span(
                30,
                "If Head owns a small incorporated business",
                "buy more stock in the company.",
            ),
        ),
        34: (
            span(
                34, "G50-52 .", 'should be "before any taxes or deductions".'
            ),
            span(34, "G52b .", "1995 Job Supplement"),
        ),
        35: ((0, page_size(35)),),
        36: (
            span(36, "DO NOT CROSS OFF OFUMs", "still in the FU."),
            span(36, "G64-72.", "Use one booklet for each additional OFUM."),
        ),
        38: (span(38, "G75.", "See instructions for B79."),),
        39: (
            span(39, "G92-98.", "Please provide detail for each amount."),
            span(39, "G92-94ff.", "work hours for each labor income."),
        ),
        66: (
            span(66, "K36-41.", "for jobs."),
            span(
                66, "K44.", "Thirty-five hours or more per week is full-time."
            ),
        ),
        67: (
            span(67, "L4-5.", "collection of occupation information)."),
            span(67, "L6.", "in the labor force"),
            span(67, "L11-12.", "with the same company does count."),
        ),
    }

    def inside(page: int, start: int, end: int) -> bool:
        return any(
            window_start <= start < end <= window_end
            for window_start, window_end in source_windows.get(page, ())
        )

    specs: dict[tuple[int, int, int, str], dict[str, Any]] = {}

    def add(
        page: int,
        start: int,
        end: int,
        kind: str,
        routes: Sequence[Sequence[tuple[int, int, int]]] = ((),),
        note: str = "Exact source atom retained after whole-page review.",
    ) -> None:
        start, end = trim_span(page, start, end)
        key = (page, start, end, kind)
        route_set = {tuple(route) for route in routes}
        current = specs.get(key)
        if current is None:
            specs[key] = {
                "page": page,
                "start": start,
                "end": end,
                "kind": kind,
                "routes": route_set,
                "note": note,
            }
        else:
            current["routes"].update(route_set)

    # 1. Independent lexeme re-derivation inside the reviewed windows.  The
    #    printed possessive role form inside typographic quotes is restored:
    #    the stage-1 role pattern only quotes the non-possessive WIFE, so it
    #    truncates '"Wife\'s"' to 'Wife\'s' and loses the printed distinction
    #    between a legal Wife and a "Wife".
    detected: list[dict[str, Any]] = []
    for page_number, page_text in enumerate(page_texts, start=1):
        if page_number not in source_windows:
            continue
        rows, _line_count = (
            annotation.stage1_candidates.detect_page_candidates(
                page_text,
                source_document_id=source_document_id,
                interview_wave=interview_wave,
                page_number=page_number,
            )
        )
        raw = page_bytes[page_number - 1]
        for row in rows:
            kind = row["occurrence_kind_candidate"]
            if kind not in DETECTED_KINDS:
                continue
            start = row["utf8_byte_start"]
            end = row["utf8_byte_end"]
            if not inside(page_number, start, end):
                continue
            if (page_number, kind, row["matched_text"]) in REVIEWED_FALSE:
                continue
            note = "Reviewer-approved atom independently re-derived from source bytes."
            if (
                kind == "role_anchor"
                and row["matched_text"].lower().endswith("'s")
                and start > 0
                and raw[start - 1 : start] == b'"'
                and raw[end : end + 1] == b'"'
            ):
                start -= 1
                end += 1
                note = (
                    "Reviewed role span corrected to the complete printed "
                    'quoted possessive form; the printed "Wife\'s" is not the '
                    "unquoted Wife's."
                )
            detected.append(
                {
                    "page": page_number,
                    "start": start,
                    "end": end,
                    "kind": kind,
                    "note": note,
                }
            )

    # A corrected quoted role atom supersedes the unquoted detector fragment
    # nested inside it; one semantic atom is retained at each same-kind span.
    corrected_role_spans = {
        (row["page"], row["start"], row["end"])
        for row in detected
        if row["kind"] == "role_anchor" and "corrected" in row["note"]
    }
    for row in detected:
        if row["kind"] == "role_anchor" and any(
            page == row["page"]
            and start <= row["start"] < row["end"] <= end
            and (start, end) != (row["start"], row["end"])
            for page, start, end in corrected_role_spans
        ):
            continue
        add(
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
            note=row["note"],
        )

    # 2. Hand-specified complete source atoms for the five clause-granular
    #    kinds.  Every one was read off the page bytes; the stage-1 rows of
    #    these kinds are trimmed physical lines that truncate the clause.
    for page, kind, opening, closing, nth, close_nth in MANUAL_ATOMS:
        start, end = span(page, opening, closing, nth, close_nth)
        if not inside(page, start, end):
            raise ValueError(
                f"manual atom outside reviewed window: page {page} {kind}"
            )
        add(
            page,
            start,
            end,
            kind,
            note=(
                "Complete printed source clause specified by whole-page review."
            ),
        )
    return _seal(
        document,
        page_texts,
        page_bytes,
        source_document_id,
        specs,
        span,
    )


def _seal(
    document: Any,
    page_texts: Sequence[str],
    page_bytes: Sequence[bytes],
    source_document_id: str,
    specs: dict[tuple[int, int, int, str], dict[str, Any]],
    span: Any,
) -> dict[str, Any]:
    """Resolve printed scope, classify anchors, and seal the review object."""

    ordered_specs = sorted(
        specs.values(),
        key=lambda row: (
            row["page"],
            row["start"],
            row["end"],
            annotation.KIND_ORDER[row["kind"]],
        ),
    )

    # This manual states conditions as running prose; it prints no skip tree.
    # The only source-explicit scope is printed containment: an atom that
    # begins strictly inside a conditional clause is governed by it, and a
    # clause inside another clause extends it.  An atom that begins on the
    # clause's own first byte is part of the printed condition rather than of
    # its consequent, so it stays unconditional, as does every atom outside
    # any clause.
    flow_rows = [
        row for row in ordered_specs if row["kind"] == "flow_branch_label"
    ]
    flow_by_key = {
        (row["page"], row["start"], row["end"]): row for row in flow_rows
    }
    if len(flow_by_key) != len(flow_rows):
        raise ValueError("duplicate flow source key")

    def containers(row: dict[str, Any]) -> tuple[tuple[int, int, int], ...]:
        chain = [
            key
            for key in flow_by_key
            if key[0] == row["page"]
            and key[1] < row["start"]
            and row["end"] <= key[2]
        ]
        chain.sort(key=lambda key: (key[1], -key[2]))
        return tuple(chain)

    for row in ordered_specs:
        row["routes"] = {containers(row)}

    resolved_flow_paths: dict[tuple[int, int, int], list[list[str]]] = {}
    resolved_flow_path_sets: dict[
        tuple[int, int, int], set[tuple[str, ...]]
    ] = {}
    resolved_route_cache: dict[tuple[tuple[int, int, int], ...], list[str]] = (
        {}
    )

    def resolve_route(route: Sequence[tuple[int, int, int]]) -> list[str]:
        route_key = tuple(route)
        cached = resolved_route_cache.get(route_key)
        if cached is not None:
            return cached
        prefix: list[str] = []
        for parent_key in route_key:
            parent = flow_by_key[parent_key]
            if tuple(prefix) not in resolved_flow_path_sets[parent_key]:
                raise ValueError(
                    f"flow ancestry cannot resolve {route_key} via {parent_key}"
                )
            prefix.append(
                annotation._review_branch_ref(
                    parent["review_id"],
                    prefix,
                    len(resolved_flow_paths[parent_key]),
                )
            )
        resolved_route_cache[route_key] = prefix
        return prefix

    for row in flow_rows:
        row["review_id"] = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )
    for row in sorted(
        flow_rows, key=lambda item: (item["page"], item["start"], -item["end"])
    ):
        key = (row["page"], row["start"], row["end"])
        resolved = [resolve_route(route) for route in sorted(row["routes"])]
        resolved_flow_paths[key] = resolved
        resolved_flow_path_sets[key] = {
            tuple(parent_path) for parent_path in resolved
        }

    occurrence_specs: list[dict[str, Any]] = []
    id_by_key: dict[tuple[int, int, int, str], str] = {}
    for row in ordered_specs:
        review_occurrence_id = _review_id(
            source_document_id,
            page_texts,
            row["page"],
            row["start"],
            row["end"],
            row["kind"],
        )
        id_by_key[(row["page"], row["start"], row["end"], row["kind"])] = (
            review_occurrence_id
        )
        occurrence_specs.append(
            {
                "review_occurrence_id": review_occurrence_id,
                "page_number": row["page"],
                "utf8_byte_start": row["start"],
                "utf8_byte_end": row["end"],
                "occurrence_kind": row["kind"],
                "parent_review_branch_paths": [
                    resolve_route(route) for route in sorted(row["routes"])
                ],
                "review_note": row["note"],
            }
        )

    occurrence_by_id = {
        spec["review_occurrence_id"]: spec for spec in occurrence_specs
    }
    parent_anchor_specs = [
        spec
        for spec in occurrence_specs
        if spec["occurrence_kind"]
        in {
            "job_anchor",
            "role_total_anchor",
            "farm_aggregate_anchor",
            "business_aggregate_anchor",
        }
    ]

    def branch_compatible(
        source: dict[str, Any], parent: dict[str, Any]
    ) -> bool:
        return any(
            source_path[: min(len(source_path), len(parent_path))]
            == parent_path[: min(len(source_path), len(parent_path))]
            for source_path in source["parent_review_branch_paths"]
            for parent_path in parent["parent_review_branch_paths"]
        )

    local_anchor_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        kind = spec["occurrence_kind"]
        if kind not in annotation.ANCHOR_KINDS:
            continue
        page = spec["page_number"]
        raw = page_bytes[page - 1][
            spec["utf8_byte_start"] : spec["utf8_byte_end"]
        ]
        label = raw.decode("utf-8", errors="strict")
        if kind == "role_anchor":
            node_domain = "role"
            classification = annotation.stage1_candidates._role_classification(
                label
            )
        else:
            node_domain, classification = annotation.ANCHOR_CLASSIFICATION[
                kind
            ]
        printed_identifier = annotation._source_printed_identifier(
            page_texts[page - 1], spec["utf8_byte_start"]
        )
        parent_ids: list[str] = []
        if kind in {"context_anchor", "remuneration_component_anchor"}:
            nested = [
                parent
                for parent in parent_anchor_specs
                if parent["page_number"] == page
                and branch_compatible(spec, parent)
                and (
                    spec["utf8_byte_start"]
                    <= parent["utf8_byte_start"]
                    < parent["utf8_byte_end"]
                    <= spec["utf8_byte_end"]
                    or parent["utf8_byte_start"]
                    <= spec["utf8_byte_start"]
                    < spec["utf8_byte_end"]
                    <= parent["utf8_byte_end"]
                )
            ]
            parent_ids = [parent["review_occurrence_id"] for parent in nested]
            parent_ids.sort(
                key=lambda review_id: occurrence_specs.index(
                    occurrence_by_id[review_id]
                )
            )
        if kind not in {"context_anchor", "remuneration_component_anchor"}:
            parent_note = "Parent resolution is not applicable to this non-component anchor."
        elif parent_ids:
            parent_note = (
                "Explicit source-local parent anchors were verified in the "
                "same source block."
            )
        else:
            parent_note = (
                "Whole-page review found no explicit source-local parent "
                "anchor; parent resolution is preserved for later global "
                "assembly."
            )
        local_anchor_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "node_domain": node_domain,
                "classification": classification,
                "printed_identifier": printed_identifier,
                "parent_review_occurrence_ids": parent_ids,
                "parent_resolution_note": parent_note,
                "classification_status": "provisional_document_local",
            }
        )

    occurrence_order = {
        spec["review_occurrence_id"]: position
        for position, spec in enumerate(occurrence_specs)
    }
    repeat_alias_specs: list[dict[str, Any]] = []
    for spec in occurrence_specs:
        if spec["occurrence_kind"] != "repeat_or_alias_instruction":
            continue
        coordinate = (
            spec["page_number"],
            spec["utf8_byte_start"],
            spec["utf8_byte_end"],
        )
        binding = LOCAL_REPEAT_BINDINGS.get(coordinate[0], {}).get(
            (coordinate[1], coordinate[2])
        )
        relation = RELATION_BY_PAGE.get(coordinate[0], {}).get(
            (coordinate[1], coordinate[2]), "explicit_cross_reference"
        )
        canonical_ids: list[str] = []
        alias_ids: list[str] = []
        if binding is not None:
            canonical_ids = sorted(
                [id_by_key[key] for key in binding["canonical"]],
                key=occurrence_order.__getitem__,
            )
            alias_ids = sorted(
                [id_by_key[key] for key in binding["alias"]],
                key=occurrence_order.__getitem__,
            )
        evidence_ids = sorted(
            {spec["review_occurrence_id"], *canonical_ids, *alias_ids},
            key=occurrence_order.__getitem__,
        )
        repeat_alias_specs.append(
            {
                "review_occurrence_id": spec["review_occurrence_id"],
                "relation": relation,
                "alias_anchor_review_occurrence_ids": alias_ids,
                "canonical_anchor_review_occurrence_ids": canonical_ids,
                "evidence_review_occurrence_ids": evidence_ids,
                "target_scope": (
                    "document_local"
                    if binding is not None
                    else "cross_document"
                ),
                "resolution_status": (
                    "document_local_source_evidence_complete"
                    if binding is not None
                    else "preserved_for_global_resolution"
                ),
            }
        )

    counts_by_page = Counter(spec["page_number"] for spec in occurrence_specs)
    page_review_rows = [
        {
            "page_number": page_number,
            "page_text_utf8_sha256": annotation._sha256(
                page_text.encode("utf-8")
            ),
            "whole_page_review_complete": True,
            "review_status": "complete",
            "review_note": (
                "Whole page reviewed against exact source bytes; "
                f"{counts_by_page[page_number]} source occurrence atoms retained."
            ),
        }
        for page_number, page_text in enumerate(page_texts, start=1)
    ]
    review: dict[str, Any] = {
        "schema_version": annotation.REVIEW_SCHEMA_VERSION,
        "review_id": "rq-stage2-source-review:"
        + annotation._canonical_digest(
            [source_document_id, annotation.DOCUMENT_SOURCE_POSITION]
        ),
        "authority_kind": "reviewer_authored_source_bytes_only_nonauthority",
        "document_source_position": annotation.DOCUMENT_SOURCE_POSITION,
        "source_document_id": source_document_id,
        "review_method": {
            "source_rows_derived_from_page_bytes": True,
            "whole_page_review": (
                "all_69_pages_including_empty_occurrence_pages"
            ),
            "span_granularity": (
                "exact_utf8_lexeme_physical_line_or_source_block"
            ),
            "candidate_nonselection": (
                "candidates_joined_only_after_source_rows_complete"
            ),
            "global_ids_assigned": False,
        },
        "page_review_rows": page_review_rows,
        "occurrence_specs": occurrence_specs,
        "local_anchor_specs": local_anchor_specs,
        "repeat_alias_specs": repeat_alias_specs,
        "integrity": {
            "canonicalization": annotation.CANONICALIZATION,
            "content_sha256": "0" * 64,
        },
        "status": "complete",
    }
    review["integrity"]["content_sha256"] = annotation._content_sha256(review)
    annotation.validate_review(review, document, page_texts)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    review = author_review()
    annotation._write_or_check(
        annotation.REVIEW_PATH, annotation._canonical_bytes(review), args.check
    )
    counts = Counter(
        row["occurrence_kind"] for row in review["occurrence_specs"]
    )
    print(
        f"{'checked' if args.check else 'wrote'} "
        f"{annotation.REVIEW_PATH.relative_to(ROOT)}: "
        f"{len(review['occurrence_specs'])} occurrences {dict(counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
