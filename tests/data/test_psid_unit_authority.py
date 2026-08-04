"""Tests for the Amendment 10 (§24) unit-authority machinery."""

from __future__ import annotations

import hashlib
import importlib.util
import re
from collections import Counter
from pathlib import Path

import pytest

import populace_dynamics.data.psid_unit_authority as unit_authority
from populace_dynamics.data.psid_unit_authority import (
    ACTUAL_CANDIDATES,
    ACTUAL_CLAUSE_TABLE,
    ACTUAL_NO_DENOTATION_CANDIDATES,
    ANCHORS,
    ARTIFACT_PARTITION,
    CLAUSE_TABLE,
    COMPILED_TERMINALS,
    FAILURE_TERMINALS,
    NO_UNIT,
    TERMINAL_ORDER,
    UNIT_ABSENT_RESOLUTION_REASON,
    UNIT_VOCABULARY,
    actual_candidate_disposition,
    actual_candidate_table,
    actual_candidates,
    artifact_of_position,
    canonical_json_bytes,
    canonical_sha256,
    clause_occurrences,
    coding_candidate_disposition,
    coding_candidate_table,
    coding_candidates,
    denotation_candidate_disposition,
    denotation_candidate_occurrence_identity,
    denotation_candidate_overselected_count,
    denotation_candidate_start_count,
    denotation_candidate_start_partition,
    denotation_candidate_table,
    denotation_candidate_unselected_count,
    denotation_candidates,
    description_statements,
    extract_statements,
    failure_reason_rows,
    field_unit,
    normalize_description,
    segment_start_authority_table,
    statement_anchor,
    statement_disposition,
    statement_predicate,
    statement_table,
    successor_census,
    successor_terminal,
    title_header_candidate_table,
    title_header_candidates,
    title_header_disposition,
)
from populace_dynamics.data.psid_unit_predicate_authority import (
    CODING_START_AUTHORITY,
    PREDICATE_AUTHORITY,
    SEGMENT_START_AUTHORITY,
)
from populace_dynamics.data.psid_unit_title_authority import (
    TITLE_GENERIC_UNIT_FAMILIES,
    TITLE_LITERAL_FAMILIES,
    TITLE_START_AUTHORITY,
)

COMPILED = "compiled_source_numeric_grammar"
PARTIAL_RANGE = "compiled_source_numeric_grammar_partial_range_exact_replay"
INCOMPLETE = "incomplete_source_numeric_authority"
UNSUPPORTED = "unsupported_source_numeric_format"
CONFLICTING = "conflicting_source_numeric_format"
VALUE_CODE_ONLY = "value_code_domain_no_numeric_grammar"
RANGE_UNESTABLISHED = "value_code_range_physical_rendering_unestablished"

DOLLARS = "The values for this variable represent dollars and cents."
PER_HOUR = "The values for this variable represent dollars and cents per hour."
HOURS = (
    "The values for this variable represent the actual number of hours per "
    'week Wife/"Wife" worked.'
)

RAW_V31 = """Annual food standard (Needs)
This is based on the USDA Low Cost plan estimates of the weekly food costs, according to
the table below reproduced from Family Economics Review March, 1967), summed for the
family converted to annual (times 52), and adjusted for economies of scale by USDA rules
as follows:
Single person-add 20%
Two persons-add 10%
Three persons-add 5%
Four persons-no change
Five persons-deduct 5%
Six or more persons-deduct 10%
TABLE B. INDIVIDUAL FOOD STANDARD (LOW COST)
Under 3:Male=3.90
Under 3:Female=3.90
4-6:Male=4.60
4-6:Female=4.60
7-9:Male=5.50
7-9:Female=5.50
10-12:Male=6.40
10-12:Female=6.30
13-15:Male=7.40
13-15:Female=6.90
16-20:Male=8.70
16-20:Female=7.20
21-35:Male=7.50
21-35:Female=6.50
35-55:Male=6.90
35-55:Female=6.30
55+:Male=6.30
55+:Female=5.40
(NOTE that the values in this table are in 1967 dollars. This same standard will be used
in subsequent years, leaving adjustments for inflation, etc. to users.)"""

TITLE_WITNESSES = (
    ("Head's annual hours working for money", "hour"),
    (
        "Total 1967 FAMILY Real Income Net of Cost of Earning Income - In Dollars\n"
        "V322 Total 1967 Family Real Income -\n"
        "V84 Child care costs, Federal Income Tax, and 1967 Union dues for Head of family -\n"
        "V57 if added originally (free child care)",
        "united_states_dollar",
    ),
    (
        "Total 1967 Family Contractual Payments - In Dollars\n"
        "V8 Annual Mortgage payments made in 1967 (for Home owners) +\n"
        "V10 1967 Rent payments +\n"
        "V14 1967 Utilities Payments +\n"
        "V18 1967 payments for additions and repairs +\n"
        "V20 1967 Car insurance payments +\n"
        "V22 1967 Car debt payments +\n"
        "V28 Other 1967 debt payments +\n"
        "V6 Estimated annual property taxes paid in 1967 (for home owners)",
        "united_states_dollar",
    ),
    (
        "Total 1967 Family Fixed Expenditures - In Dollars\n"
        "V331 Total 1967 Family Contractual Payments +\n"
        "V37 Total 1967 Family food expenditures +\n"
        "V84 Child care costs (for families where there are children under 12 and Wife of Head\n"
        "works, or single Head of family works for money) and 1967 Union dues for HEAD of family +\n"
        "V82 Total 1967 payments to dependents outside DU (only for cases where amount was\n"
        "ascertained)",
        "united_states_dollar",
    ),
    (
        "Total 1967 Family Uncommitted Money Income - in Dollars\n"
        "V81 Total 1967 Family money income - V332 Total 1967 Family fixed expenditures",
        "united_states_dollar",
    ),
    (
        "Average Age of Head and Wife (In Years)\n"
        "This Variable is the simple average of V117 (age of Head), V118 (age of Wife). If V118 =\n"
        "00 (no wife), age of Head is recorded again.\n"
        "Average age of head and wife=36; or no wife present, and head is 36 years old.",
        "year",
    ),
    ("Elapsed Interview Length in Minutes", "minute"),
)

CURRENT_MAIN_JOB_HOUR_INPUT_CONTEXTS = (
    "BC31. If (you/he/she) were to work more hours than usual during some "
    "week, would\n(you/he/she) get paid for those extra hours of "
    "work?--CURRENT MAIN JOB",
    "DE31. If (you/she) were to work more hours than usual during some week, "
    "would (you/she)\nget paid for those extra hours of work?--CURRENT MAIN JOB",
    "DE31. If (you/he/she) were to work more hours than usual during some "
    "week, would\n(you/he/she) get paid for those extra hours of "
    "work?--CURRENT MAIN JOB",
)
CURRENT_MAIN_JOB_HOUR_INPUT_FIELDS = (
    "ER53197",
    "ER53460",
    "ER60212",
    "ER60475",
    "ER66213",
    "ER66488",
)

RAW_V100 = (
    "5. Length of Interview\n"
    "Code actual number of MINUTES (e.g. 1 hour and 10 minutes - 70 minutes)."
)
RAW_V121 = (
    "B3. Is he/she in school? (Code number of children in FU in school and "
    "living at home)\n(exclude in-laws)"
)
RAW_V155 = (
    "C20. (If Yes) What kinds of things have you done on your car(s) in the "
    "last year?\nPRIORITY CODE - highest number."
)
RAW_V194 = (
    "Thumbnail sketch evidence on housing\n"
    "PRIORITY CODE the lowest number applicable."
)
RAW_V229 = (
    "F46. About how much did you make per hour for this?\n"
    "(Code dollars and cents per hour.)"
)
RAW_V228 = (
    "F43. What did you do?\n"
    "(Code same as other occupation code (Col. 12). If two or more jobs, "
    "code the one with the\nlowest code number (highest status)"
)
RAW_V373 = (
    "Average Value Per Room in Dwelling Unit\n"
    "For Homeowners: V5 House Value / V102 Number of rooms in DU\n"
    "*For Renters: 10 x V11 Annual Rent / V102 Number of rooms in DU\n"
    "*For those who neither own nor rent: 10 x V12 Rental Value / V102     "
    "Number of rooms in DU\n"
    "xxxx. Coded in Dollars\n"
    "*(Calculated value assumes that value of DU is approximately 10 times "
    "its annual rental\nvalue)"
)
RAW_V418 = (
    "Housing and Neighborhood Quality Redone (Revised V387)\n"
    "Owns home V103 = 1\n"
    "Lives 5-30 miles from center of city of 50,000 or more V189 = 2, 3\n"
    "Single Family home V190 = 1\n"
    "Neighborhood of Single Family Houses V192 = 2\n"
    "Value per room Value - (10 x rent for non-owners) > 2000   V374=4-8\n"
    "Actual - Required rooms   V381 = 5 - 9\n"
    "No visible defects V194 = 5\n"
    "OMITS: Car Lack Felt Share\n"
    "Dwelling (Hard to Determine)\n"
    "Changes: Distance to Center, Surplus of Rooms"
)
RAW_V494 = (
    "Annual food needs standard\n"
    "Based on the USDA Low Cost plan estimates of the weekly food costs, "
    "according to the table\n"
    "below (reproduced from Family Economics Review March, 1967), summed "
    "for the family and\n"
    "converted to an annual amount and adjusted for economies of scale by "
    "USDA rules as\nfollows:\n"
    "Single person-add 20%\nTwo persons-add 10%\nThree persons-add 5%\n"
    "Four persons-no change\nFive persons-deduct 5%\n"
    "Six or more persons-deduct 10%\n"
    "INDIVIDUAL FOOD STANDARD (LOW COST)\n"
    "Under 4:Male=3.90\nUnder 4:Female=3.90\n"
    "4-6:Male=4.60\n4-6:Female=4.60\n"
    "7-9:Male=5.50\n7-9:Female=5.50\n"
    "10-12:Male=6.40\n10-12:Female=6.30\n"
    "13-15:Male=7.40\n13-15:Female=6.90\n"
    "16-20:Male=8.70\n16-20:Female=7.20\n"
    "21-35:Male=7.50\n21-35:Female=6.50\n"
    "36-55:Male=6.90\n36-55:Female=6.30\n"
    "56+:Male=6.30\n56+:Female=5.40\n"
    "(NOTE that the values for this variable are in 1967 dollars. This "
    "same standard will be\n"
    "used in both Waves I and II. Adjustments for inflation, etc. are left "
    "to users.)"
)
RAW_V2137 = "J1. Code number of things mentioned to J1"
RAW_V2192 = (
    "L25-27. (M9) Code Number of States or Countries in which R has lived "
    "including present\nlocation"
)
RAW_V2470 = (
    "Weekly Food Needs\n"
    "This variable's values are based on USDA Low-Cost Plan estimates of "
    "weekly food costs,\n"
    "according to the table below (reproduced from Family Economics "
    "Review, June 1967), summed\n"
    "for the family as it was at the time of the interview.\n"
    "INDIVIDUAL FOOD STANDARD (LOW COST)\n"
    "$3.90 for both males and females under age 4\n"
    "$4.60 for both males and females age 4-6\n"
    "$5.50 for both males and females age 7-9\n"
    "$6.40 for males age 10-12\n$6.30 for females age 10-12\n"
    "$7.40 for males age 13-15\n$6.90 for females age 13-15\n"
    "$8.70 for males age 16-20\n$7.20 for females age 16-20\n"
    "$7.50 for males age 21-35\n$6.50 for females age 21-35\n"
    "$6.90 for males age 36-55\n$6.30 for females age 36-55\n"
    "$6.30 for males age 56 and older\n"
    "$5.40 for females age 56 and older\n"
    "This same standard has been used in previous waves. Since the table is "
    "from 1967, values\n"
    "are in 1967 dollars. Adjustments for inflation, etc., are left to "
    "users.\n"
    "The actual weekly food needs in dollars and cents are coded here."
)
RAW_V3694 = """Annual Food Standard
This variable is generated by multiplying the weekly food needs (V3439) by 52 and then
making the following adjustments for economies of scale:
add
20 percent for one-person families
10 percent for 2-person families
5 percent for 3-person families;
subtract
5 percent for 5-person families
10 percent for families with six or more.
See note at V3439 (weekly food needs, used in computing this variable) regarding use of
1967 dollar values.
The code values for this variable represent the food standard for the 1974 family in whole
dollars."""
RAW_V4367 = (
    "Number of months used food stamps in 1975\n"
    "Code 1-11 for actual number of months used food stamps in 1975"
)
RAW_V4742 = "Length of Interview\nCode actual number of minutes"
RAW_V5453 = (
    "E13. How long have you been looking for work?\n"
    "Code actual number of weeks (01 - 98)"
)
RAW_V9378 = (
    "Annual 1983 Food Standard\n"
    "This variable is generated by multiplying the weekly food needs "
    "(V8853) by 52 and then\n"
    "making the following adjustments for economies of scale:\n"
    "+20% for one-person families\n+10% for two-person families\n"
    "+ 5% for three-person families\n"
    "no adjustment for four-person families\n"
    "- 5% for five-person families\n"
    "-10% for families with six or more persons\n"
    "The values represent the actual annual food standard in whole dollars "
    "for the 1983 family.\n"
    "Note that V8823 is based on a table from 1967, with 1967 dollar values."
)
RAW_V21488 = """Annual Needs Standard for the 1991 (Last Year's) Family
This is the Orshansky-type poverty threshold based on an annual food needs standard which
is derived from the weekly food costs in the preceding variable, converted to an annual
amount, and adjusted for economies of scale by USDA rules as follows:
Single person . . . . . . . . . . . .add 20%
Two persons . . . . . . . . . . . . .add 10%
Three persons . . . . . . . . . . . . add 5%
Four persons . . . .   . . . . . . .no change
Five persons . . . . . . . . . . .deduct 5%
Six or more persons . . . . . . . deduct 10%
An additional adjustment for diseconomies of small households (in
rent, etc.) was made as follows:
4.89 times the food needs for single persons
3.70 times the food needs for two-person units
3.00 times the food needs for all other units
Please refer to the Wave VII (1974) Documentation volume, pp. 39-41, and to the User Guide
for further details on the need standard. Note that this variable is not adjusted for
inflation (it is in 1967 dollars), nor is it exactly comparable to the official poverty
standard; such changes are left to users. This need standard is adjusted for changes in
family composition during 1991 and is not adjusted for farmers; see V21489 for an
income/needs measure which makes such an adjustment."""
RAW_ER2005 = """Date of Interview
The first 2 digits represent the month, the last 2 digits represent the day."""
RAW_ER3062 = """F10. During which months did you receive food stamps?--FIRST MENTION
The label for this variable is incorrect. This is actually the first mention of months
the FU received food stamps. Months are coded below with January=1, February=2, etc."""
RAW_ER12067 = """Head's and Wife's/"Wife's" Income from Unincorporated Businesses in 1996
The income reported here was collected in 1997 about tax year 1996. Dollar amounts are
based on values for the year in which they are reported. Thus, dollar amounts reported in
1997 for the prior year are in 1996 dollars.
New Immigrant Sample families (ER10002=10001-10444) have values for this variable."""
RAW_ER12079 = """Total Family Money Income in 1996
The income reported here was collected in 1997 about tax year 1996. Please note that this
variable can contain negative values. The negative values indicate a net loss, which in
waves prior to 1994 were bottom-coded at $1. These losses occur as a result of business
or farm losses.
Dollar amounts are based on values for the year in which they are reported.     Thus, dollar
amounts reported in 1997 for the prior year are in 1996 dollars.
This variable is the sum of the 1996 variables below:
taxable income of head and wife (ER12069),
transfer income of head and wife (ER12071),
taxable income of other family unit members (OFUMs) (ER12073),
transfer income of OFUMs (ER12075), and
Social Security income (ER12077).
New Immigrant Sample families (ER10002=10001-10444) have values for this variable."""
RAW_ER55305 = (
    "H6k3. (Are/Is) (you/HEAD) currently in treatment for "
    "(your/his/her) cancer, in remission,\n"
    "or has it been cured?\n"
    "IF R says can't afford insurance to get treatment, are doing nothing, "
    "etc, ENTER: 4"
)
RAW_V22842 = (
    "D23. How many years' experience does she have altogether with her "
    "present employer?\n"
    "The values for this variable in the range 001-997 represent the actual "
    "number of\n"
    'monthsWife/"Wife" has worked for the present employer.'
)
RAW_V3520 = (
    "B6. During the last year how many miles did you and your family drive in "
    "(your car/all of\n"
    "your cars)?\n"
    "The code values for this variable represent the actual number of miles "
    "per year."
)
RAW_V11959 = (
    "G45. What is the highest year of college you have completed?\n"
    "The values for this variable represent the actual number of years of "
    "college completed (1-\n"
    "4)."
)
RAW_ER70826 = (
    "K78d. Altogether, what is the highest year of college "
    "(you have/[he/she] has) completed?"
)
RAW_ER64765 = (
    "K83a. (Between [PY IW DATE] and now, how/How) many years of school did "
    "(you/she) complete\n"
    "outside of the U.S.?"
)
RAW_ER64904 = (
    "L83a. (Between [PY IW DATE] and now, how/How) many years of school did "
    "(you/he/she)\n"
    "complete outside of the U.S.?"
)
RAW_ER64764 = (
    "K83. In what month and year did (you/she) receive(your/her) highest "
    "degree?--YEAR"
)
RAW_ER64907 = (
    "L84a. (Earlier you said [you are/[HEAD] is] still in school.)   What "
    "grade or year (are/is)\n"
    "(you/he/she) attending?"
)
RAW_V10475 = (
    "C25. How much paid vacation or personal time do you get each year?- HOURS\n"
    "The values for this variable represent the actual number of hours "
    "(0001-2080) per year."
)
RAW_V10492 = (
    "C40. What amount or percent of pay do you voluntary contribute "
    "currently?-TYPE OF\n"
    "RESPONSE"
)
RAW_V10734 = (
    "F63. When did your (Wife/friend) start working in her present "
    "(position/work situation)?-\n"
    "TOTAL MONTHS\n"
    "The values for this variable represent the actual number of months "
    '(001-997) Wife/"Wife"\n'
    "has worked in her present position or work situation."
)
RAW_V17887 = (
    "G33. Was that disability, retirement, survivor's benefits, or what?- "
    'Wife/"WIFE"'
)
RAW_V22543 = (
    "B48. In what month and year did you start working for that (other) "
    "main-job employer?-YEAR\n"
    "The values for this variable represent the year Head started working "
    "for his/her other\n"
    "main-job employer."
)
RAW_V22553 = (
    "B56. How much were you making at that time?--SELF EMPLOYED -TIME UNIT\n"
    "B57. What was your (HEAD's) final wage or salary when you left that "
    "employer?--WORK FOR\n"
    "OTHERS-TIME UNIT"
)
RAW_ER47555 = (
    "BC6. When did you (HEAD) start and when did you stop working for this "
    "employer?   Please\n"
    "give me all of the start and stop dates if you have gone to work for "
    "(this\n"
    "employer/yourself) more than once.- BEGINNING MONTH FOR JOB 3"
)
RAW_ER27094 = (
    "H12b. How often do you do light or moderate activities for at least 10 "
    "minutes that cause\n"
    "only light sweating or slight to moderate increases in breathing or "
    "heart rate?--NUMBER OF\n"
    "TIMES"
)
RAW_ER27217 = (
    "H36b. How often does she do light or moderate activities for at least "
    "10 minutes that\n"
    "cause only light sweating or slight to moderate increases in breathing "
    "or heart rate?--\n"
    "NUMBER OF TIMES"
)
RAW_ER49614 = (
    "H12a. (I know you already told me about (your/HEAD's) condition, but I "
    "need to ask these\n"
    "next questions anyway.)\n"
    "The next questions are about physical activities (exercise, sports, "
    "physically active\n"
    "hobbies...) that (you/HEAD) may do in (your/his/her) leisure time.\n"
    "(In (your/HEAD's) leisure time,) how often (do/does) (you/HEAD) do "
    "VIGOROUS physical\n"
    "activities for at least 10 minutes that cause heavy sweating or large "
    "increases in\n"
    "breathing or heart rate?--NUMBER OF TIMES"
)
RAW_ER52049 = (
    "M18. [WIFE ONLY: During 2010, did (you/WIFE) do volunteer activity at or "
    "through\n"
    "(your/her) church, synagogue, or mosque, such as serving on a committee, "
    "assisting in\n"
    "worship, teaching, or helping others through programs organized by your "
    "place of worship?\n"
    "Please do not include volunteering through schools, hospitals, and other "
    "charities run by\n"
    "religious organizations.]\n"
    "[BOTH: And during 2010, did (you/WIFE) do volunteer activity at or "
    "through (your/her)\n"
    "church, synagogue, or mosque, not including any volunteering through "
    "schools, hospitals,\n"
    "and other charities run by religious organizations?]--WIFE\n"
    "See note at ER52026."
)
RAW_ER47459 = (
    "BC14B4. How many hours did that overtime amount to (on (all of) "
    "(your/his/her) (job/jobs)\n"
    "in 2010)?--AMOUNT"
)
RAW_ER47460 = (
    "BC14B4. How many hours did that overtime amount to (on (all of) "
    "(your/his/her) (job/jobs)\n"
    "in 2010)?--TIME UNIT"
)
RAW_ER66175 = (
    "BC14b4. How many hours did that overtime amount to (on (all of) "
    "(your/his/her) (job/jobs)\n"
    "in 2016)?--AMOUNT"
)
RAW_ER66176 = (
    "BC14b4. How many hours did that overtime amount to (on (all of) "
    "(your/his/her) (job/jobs)\n"
    "in 2016)?--TIME UNIT"
)
RAW_ER3060 = (
    "F9. How many dollars' worth of stamps did you get in 1993?--AMOUNT"
)
RAW_ER3061 = (
    "F9. How many dollars' worth of stamps did you get in 1993?--TIME UNIT"
)
RAW_ER15249 = (
    "P62. Can you estimate what you expect these benefits to be? Either in "
    "dollars per month\n"
    "or year, or as a percent of your pay when you left that job?--AMOUNT FOR "
    "FIRST PENSION"
)
RAW_ER15250 = (
    "P62. Can you estimate what you expect these benefits to be? Either in "
    "dollars per month\n"
    "or year, or as a percent of your pay when you left that job?--TIME UNIT "
    "FOR FIRST PENSION"
)
RAW_ER15251 = (
    "P62. Can you estimate what you expect these benefits to be? Either in "
    "dollars per month\n"
    "or year, or as a percent of your pay when you left that job?--PERCENT OF "
    "PAY FOR FIRST\n"
    "PENSION"
)
RAW_ER15252 = (
    "P62. Can you estimate what you expect these benefits to be? Either in "
    "dollars per month\n"
    "or year, or as a percent of your pay when you left that job?--LUMP SUM "
    "PAYMENT FOR FIRST\n"
    "PENSION"
)
RAW_ER60084 = (
    "A27d. In what month and year did the foreclosure start?--MONTH--SECOND "
    "MORTGAGE"
)
RAW_ER62267 = (
    "P62k. And what was (your/her) pay when (you/she) left that job? "
    "--SPOUSE/PARTNER JOB #1--\n"
    "TIME UNIT"
)
RAW_ER66716 = (
    "F1b. (In a typical week, how many hours [do you/does [he/she]] spend) "
    "Doing personal care\n"
    "activities, for example, grooming, getting ready for the day, or taking "
    "care of\n"
    "(your/his/her) health needs?\n"
    "The values for this variable represent the actual number of hours per "
    "week the Reference\n"
    "Person spends on personal care activities."
)

ROUND2_RAW_DESCRIPTIONS = (
    RAW_V31,
    RAW_V100,
    RAW_V121,
    RAW_V155,
    RAW_V194,
    RAW_V228,
    RAW_V229,
    RAW_V373,
    RAW_V418,
    RAW_V494,
    RAW_V2137,
    RAW_V2192,
    RAW_V2470,
    RAW_V3694,
    RAW_V4367,
    RAW_V4742,
    RAW_V5453,
    RAW_V9378,
    RAW_V21488,
    RAW_ER2005,
    RAW_ER3062,
    RAW_ER12067,
    RAW_ER12079,
    RAW_ER55305,
)


# --------------------------------------------------------------------------
# Stage 1 — normalization
# --------------------------------------------------------------------------


def test_normalization_is_exactly_three_steps() -> None:
    assert normalize_description("a\nb") == "a b"
    assert normalize_description("a   b") == "a b"
    assert normalize_description("  a\n   b  ") == "a b"
    assert normalize_description(None) == ""


def test_normalization_preserves_case_punctuation_and_quotes() -> None:
    raw = "Wife's/\"Wife's\" PAY’ — A.B."
    assert normalize_description(raw) == raw


def test_normalization_does_not_fold_tabs_or_other_whitespace() -> None:
    # Only LF and U+0020 participate; the derivation already stripped
    # per-line leading and trailing tabs, so a surviving tab is content.
    assert normalize_description("a\tb") == "a\tb"
    assert normalize_description("\ta\t") == "\ta\t"
    assert normalize_description(" \ta\t ") == "\ta\t"
    assert normalize_description("\ra\r") == "\ra\r"
    assert normalize_description("\va\v") == "\va\v"
    assert normalize_description("\N{NO-BREAK SPACE}a\N{NO-BREAK SPACE}") == (
        "\N{NO-BREAK SPACE}a\N{NO-BREAK SPACE}"
    )


# --------------------------------------------------------------------------
# Stage 2 — statement extraction
# --------------------------------------------------------------------------


def test_statement_requires_a_space_or_text_start_before_the_anchor() -> None:
    assert extract_statements(DOLLARS) == (DOLLARS,)
    assert extract_statements("AMOUNT " + DOLLARS) == (DOLLARS,)
    # Glued on the left, so neither the capitalized opener nor the
    # lowercase one that would otherwise start at "values" can open.
    assert extract_statements("xvalues for this variable represent x.") == ()


def test_nested_anchor_cannot_open_a_second_statement() -> None:
    text = "The value for this variable represents dollars and cents."
    assert extract_statements(text) == (text,)
    assert statement_anchor(text) == "The value for this variable "


def test_terminator_ignores_an_interior_decimal_point() -> None:
    text = "The values for this variable represent 1.5 hours per week."
    assert extract_statements(text) == (text,)


def test_terminator_stops_at_the_first_period_before_a_space() -> None:
    text = "The values for this variable represent dollars. Something else."
    assert extract_statements(text) == (
        "The values for this variable represent dollars.",
    )


def test_unterminated_statement_runs_to_the_end_of_the_text() -> None:
    text = "The values for this variable represent dollars and cents"
    assert extract_statements(text) == (text,)


def test_two_statements_are_returned_in_text_order() -> None:
    text = f"{DOLLARS} {HOURS}"
    assert extract_statements(text) == (DOLLARS, HOURS)


def test_every_anchor_is_reachable() -> None:
    for anchor in ANCHORS:
        text = f"{anchor}dollars and cents."
        assert extract_statements(text) == (text,)


@pytest.mark.parametrize(
    "text",
    [
        "The actual weekly food needs in dollars and cents are coded here.",
        (
            "The code values represent the actual number of persons "
            "currently in the FU."
        ),
        (
            "The values represent the actual annual food standard in whole "
            "dollars for the 1983 family."
        ),
    ],
)
def test_omitted_denotation_families_are_selected(text: str) -> None:
    assert extract_statements(text) == (text,)
    assert statement_disposition(text)[0] is not None


def test_actual_residual_selector_covers_line_start_and_embedded_tail() -> (
    None
):
    description = (
        "Question text Actual number of weeks\n"
        "Actual dollars and cents per hour"
    )
    assert actual_candidates(description) == (
        "Actual number of weeks",
        "Actual dollars and cents per hour",
    )
    assert description_statements(description) == actual_candidates(
        description
    )


def test_actual_explicit_no_denotation_is_not_a_statement() -> None:
    candidate = "Actual - Required rooms   V381 = 5 - 9"
    assert candidate in actual_candidates(RAW_V418)
    assert actual_candidate_disposition(candidate) == "explicit_no_denotation"
    assert description_statements(RAW_V418) == ()
    assert field_unit(RAW_V418) == (None, "no_denotation_statement")


def test_actual_candidate_adjudication_is_closed_and_fail_closed() -> None:
    assert len(ACTUAL_CANDIDATES) == len(set(ACTUAL_CANDIDATES)) == 82
    assert ACTUAL_NO_DENOTATION_CANDIDATES < set(ACTUAL_CANDIDATES)
    assert (
        actual_candidate_disposition("Actual number of weeks")
        == "whole_domain_denotation"
    )


def test_exhaustive_candidate_selector_covers_lexemes_and_actual_lines() -> (
    None
):
    candidates = denotation_candidates(RAW_V4742)
    assert len(candidates) == denotation_candidate_start_count(RAW_V4742)
    assert candidates[0] == "Length of Interview Code actual number of minutes"
    assert "Code actual number of minutes" in candidates
    assert "minutes" in candidates
    assert denotation_candidate_unselected_count(RAW_V4742) == 0
    assert denotation_candidate_overselected_count(RAW_V4742) == 0
    assert (
        actual_candidate_disposition(
            "Actual - Required rooms = 2 or more (V891 EQ 5 - 8)"
        )
        == "explicit_no_denotation"
    )
    assert (
        actual_candidate_disposition("Actual furlongs per fortnight")
        == "unadjudicated_no_denotation"
    )
    assert (
        denotation_candidate_disposition(
            "A component represents a lookup value."
        )
        == "unadjudicated_context_free_candidate"
    )
    assert statement_disposition("Actual furlongs per fortnight") == (
        None,
        "unadjudicated_denotation_candidate",
    )


@pytest.mark.parametrize(
    ("description", "candidate", "statement", "unit"),
    [
        (
            RAW_V100,
            "Code actual number of MINUTES (e.g.",
            "Code actual number of MINUTES (e.g. 1 hour and 10 minutes - "
            "70 minutes).",
            "minute",
        ),
        (
            RAW_V121,
            "Code number of children in FU in school and living at home) "
            "(exclude in-laws)",
            "Code number of children in FU in school and living at home) "
            "(exclude in-laws)",
            "count",
        ),
        (
            RAW_V229,
            "Code dollars and cents per hour.)",
            "Code dollars and cents per hour.)",
            "united_states_dollar_per_hour",
        ),
        (
            RAW_V373,
            "Coded in Dollars *(Calculated value assumes that value of DU is "
            "approximately 10 times its annual rental value)",
            "Coded in Dollars",
            "united_states_dollar",
        ),
        (
            RAW_V2137,
            "Code number of things mentioned to J1",
            "Code number of things mentioned to J1",
            "count",
        ),
        (
            RAW_V2192,
            "Code Number of States or Countries in which R has lived including "
            "present location",
            "Code Number of States or Countries in which R has lived including "
            "present location",
            "count",
        ),
        (
            RAW_V4367,
            "Code 1-11 for actual number of months used food stamps in 1975",
            "Code 1-11 for actual number of months used food stamps in 1975",
            "month",
        ),
        (
            RAW_V4742,
            "Code actual number of minutes",
            "Code actual number of minutes",
            "minute",
        ),
        (
            RAW_V5453,
            "Code actual number of weeks (01 - 98)",
            "Code actual number of weeks (01 - 98)",
            "week",
        ),
    ],
)
def test_complete_raw_coding_descriptions_name_the_grounded_unit(
    description: str,
    candidate: str,
    statement: str,
    unit: str,
) -> None:
    assert candidate in coding_candidates(description)
    assert coding_candidate_disposition(candidate) == (
        "whole_domain_denotation"
    )
    assert statement in description_statements(description)
    assert statement_disposition(statement) == (unit, "unit_naming_clause")
    assert field_unit(description)[0] == unit


@pytest.mark.parametrize(
    ("description", "statement"),
    [
        (RAW_V155, "CODE - highest number."),
        (RAW_V194, "CODE the lowest number applicable."),
    ],
)
def test_complete_raw_priority_code_descriptions_are_visible_defeaters(
    description: str,
    statement: str,
) -> None:
    assert coding_candidates(description) == (statement,)
    assert coding_candidate_disposition(statement) == (
        "whole_domain_denotation"
    )
    assert description_statements(description) == (statement,)
    assert statement_disposition(statement) == (None, "defeating_clause")
    assert field_unit(description) == (
        None,
        "defeated_denotation_statement",
    )


def test_complete_raw_enter_colon_instruction_is_explicitly_nonwhole() -> None:
    candidate = "ENTER: 4"
    assert coding_candidates(RAW_ER55305) == (candidate,)
    assert coding_candidate_disposition(candidate) == (
        "explicit_no_whole_domain_denotation"
    )
    assert description_statements(RAW_ER55305) == ()
    assert field_unit(RAW_ER55305) == (None, "no_denotation_statement")


@pytest.mark.parametrize(
    "description",
    [
        "Code actual number of MINUTES (e.g.",
        "Code actual number of MINUTES (e.g. fabricated continuation.",
        "Code same as other occupation code (Col.",
        "Code same as other occupation code (Col. fabricated continuation.",
    ],
)
def test_truncated_or_fabricated_abbreviation_span_cannot_inherit_authority(
    description: str,
) -> None:
    candidate = coding_candidates(description)[0]
    assert candidate in {
        "Code actual number of MINUTES (e.g.",
        "Code same as other occupation code (Col.",
    }
    assert coding_candidate_disposition(candidate) == (
        "whole_domain_denotation"
    )
    assert description_statements(description) == (candidate,)
    assert statement_disposition(candidate) == (
        None,
        "unadjudicated_denotation_candidate",
    )
    expected_reason = (
        "defeated_title_denotation"
        if "MINUTES" in description
        else "defeated_denotation_statement"
    )
    assert field_unit(description) == (None, expected_reason)


def test_full_abbreviation_spans_retain_only_their_exact_adjudication() -> (
    None
):
    assert field_unit(RAW_V100)[0] == "minute"
    assert field_unit(RAW_V228) == (None, "no_statement_names_a_unit")


def test_complete_raw_v494_copular_statement_names_1967_dollars() -> None:
    statement = "the values for this variable are in 1967 dollars."
    assert statement in description_statements(RAW_V494)
    assert statement_predicate(statement) == "in 1967 dollars."
    assert statement_disposition(statement) == (
        "united_states_dollar",
        "unit_naming_clause",
    )
    assert field_unit(RAW_V494) == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


def test_v31_input_table_does_not_denote_the_annual_family_total() -> None:
    candidates = title_header_candidates(RAW_V31)
    assert Counter(candidate[0] for candidate in candidates) == {
        "weekly_morphology": 1,
        "percent_symbol": 5,
        "nominal_dollar_token": 1,
        "nominal_year_token": 1,
    }
    table = title_header_candidate_table(
        [_row(1968, "V31", COMPILED, RAW_V31)]
    )[0]
    assert table["candidate_count"] == 8
    assert {
        (row["adjudication"], row["reason"])
        for row in table["candidate_adjudications"]
    } == {
        (
            "explicit_no_whole_domain_denotation",
            "input_table_or_subrange_not_field_denotation",
        )
    }
    assert description_statements(RAW_V31) == ()
    assert title_header_disposition(RAW_V31) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )
    assert field_unit(RAW_V31) == (None, "no_denotation_statement")


@pytest.mark.parametrize(("description", "unit"), TITLE_WITNESSES)
def test_exact_title_header_witnesses_denote_the_whole_field(
    description: str, unit: str
) -> None:
    assert title_header_candidates(description)
    assert title_header_disposition(description) == (
        unit,
        "derived_from_title_denotation",
    )
    assert field_unit(description) == (unit, "derived_from_title_denotation")
    assert denotation_candidate_unselected_count(description) == 0
    assert denotation_candidate_overselected_count(description) == 0


def test_title_clause_maximal_munch_drops_nested_shorter_unit_tokens() -> None:
    candidates = title_header_candidates(
        "Annual hours a week and Dollar Amount in Dollars"
    )
    assert ("hours_a_week", 7, 19, "hours a week") in candidates
    assert not any(row[0] == "nominal_hour_token" for row in candidates)
    assert ("dollar_amount", 24, 37, "Dollar Amount") in candidates
    assert not any(row[0] == "nominal_dollar_token" for row in candidates)


def test_title_header_continuation_includes_uppercase_wrapped_label_lines() -> (
    None
):
    wrapped = "Prompt--\nDAYS\nYEARS"
    assert unit_authority._raw_title(wrapped) == wrapped
    assert title_header_candidates(wrapped) == (
        ("nominal_day_token", 9, 13, "DAYS"),
        ("nominal_year_token", 14, 19, "YEARS"),
    )
    assert unit_authority._raw_title("Prompt--\nDAYS\nlower prose") == (
        "Prompt--\nDAYS"
    )
    assert title_header_candidates("Prompt--\nTEXT\nDAYS") == (
        ("nominal_day_token", 14, 18, "DAYS"),
    )
    assert title_header_candidates("Prompt--\nlower prose\nDAYS") == (
        ("nominal_day_token", 21, 25, "DAYS"),
    )
    assert title_header_candidates("Prompt-- \nDAYS") == (
        ("nominal_day_token", 10, 14, "DAYS"),
    )
    assert title_header_candidates("Prompt-\nDAYS") == (
        ("nominal_day_token", 8, 12, "DAYS"),
    )


def test_singleton_title_selectors_cover_inline_next_line_and_wrapped_labels() -> (
    None
):
    assert unit_authority._title_selector_spans(RAW_V10475) == (
        ("single_hyphen", 68, 73, "HOURS"),
    )
    assert unit_authority._title_selector_spans(RAW_V10734)[0][0] == (
        "single_hyphen_next_line"
    )
    assert unit_authority._title_selector_spans(RAW_V10734)[0][3] == (
        "TOTAL MONTHS"
    )
    assert unit_authority._title_selector_spans(RAW_V10492)[0][3] == (
        "TYPE OF\nRESPONSE"
    )


def test_singleton_parser_checks_every_hyphen_and_exact_source_exceptions() -> (
    None
):
    assert unit_authority._title_selector_spans(RAW_V22543) == (
        ("single_hyphen", 86, 90, "YEAR"),
    )
    assert unit_authority._title_selector_spans(RAW_ER47555) == (
        ("single_hyphen", 200, 225, "BEGINNING MONTH FOR JOB 3"),
    )
    assert unit_authority._title_selector_spans(RAW_V17887) == (
        ("single_hyphen", 69, 80, 'Wife/"WIFE"'),
    )


def test_singleton_parser_deduplicates_contained_and_rejects_lookalikes() -> (
    None
):
    contained = (
        "Question? [MOST OF THE YEARS--ACCEPT FATHER SUBSTITUTE]-\n"
        "FATHER'S STATE"
    )
    spans = unit_authority._title_selector_spans(contained)
    assert len(spans) == 1
    assert spans[0][0] == "double_hyphen"
    assert spans[0][3] == "ACCEPT FATHER SUBSTITUTE]-\nFATHER'S STATE"

    for description in (
        "Prompt (BEGYR)-(ENDYR)?-",
        "Prompt COVID-19?",
        "Prompt?-Mixed Case",
        "Prompt?--DAYS",
        "Question\n-----\n-HOURS",
    ):
        assert not any(
            kind.startswith("single_hyphen")
            for kind, _start, _end, _label in (
                unit_authority._title_selector_spans(description)
            )
        )


def test_first_question_extends_header_monotonically_without_prefix_gate() -> (
    None
):
    wrapped = "Uncoded title first line\nHow many hours?\nBody prose"
    assert unit_authority._raw_title(wrapped) == (
        "Uncoded title first line\nHow many hours?"
    )
    assert title_header_candidates(wrapped) == (
        ("how_many_count_marker", 25, 33, "How many"),
        ("nominal_hour_token", 34, 39, "hours"),
    )
    assert unit_authority._raw_title("No question\nHours in body") == (
        "No question"
    )


def test_last_question_header_keeps_its_complete_physical_line() -> None:
    description = "Question? (Number of regions)\nBody prose"
    assert unit_authority._raw_title(description) == (
        "Question? (Number of regions)"
    )
    assert ("number_of_count_marker", 11, 20, "Number of") in (
        title_header_candidates(description)
    )


def test_only_exact_question_continuation_pairs_extend_one_more_line() -> None:
    admitted = (
        "C6. How many cars do you own? (Include trucks, leased cars,\n"
        "in the count if they are used as family transportation, i.e., left in by Editor)\n"
        "Body year"
    )
    assert unit_authority._raw_title(admitted) == admitted.rsplit("\n", 1)[0]

    rejected = "Question? (Include boats,\nin the count)\nBody year"
    assert unit_authority._raw_title(rejected) == "Question? (Include boats,"


def test_candidate_superdomain_exposes_body_starts_beyond_bounded_header() -> (
    None
):
    description = "Question?\nBody month\nBody year"
    assert unit_authority._raw_title(description) == "Question?"
    assert title_header_candidates(description) == (
        ("nominal_month_token", 15, 20, "month"),
        ("nominal_year_token", 26, 30, "year"),
    )


def test_full_description_offsets_keep_two_body_candidates_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    description = "Question?\nBody month\nBody year"
    digest = hashlib.sha256(description.encode("utf-8")).hexdigest()
    month, year = title_header_candidates(description)
    monkeypatch.setattr(
        unit_authority,
        "_TITLE_START_AUTHORITY",
        {
            (digest, *month): (
                "month",
                "whole_domain_denotation",
                "test_month",
            ),
            (digest, *year): (
                None,
                "explicit_no_whole_domain_denotation",
                "test_year_defeat",
            ),
        },
    )
    normalized = normalize_description(description)
    month_offset = normalized.index("month")
    year_offset = normalized.index("year")
    assert unit_authority._production_title_start_offsets(description) == {
        month_offset
    }
    assert unit_authority._title_start_tags(description) == {
        month_offset: "W",
        year_offset: "N",
    }


def test_title_defeat_does_not_demote_statement_whole_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    description = "Token dollars."
    segment = normalize_description(description)
    starts = unit_authority._word_start_offsets(segment)
    dollar_offset = segment.index("dollars")
    vector = ["N"] * len(starts)
    vector[starts.index(dollar_offset)] = "W"
    monkeypatch.setattr(
        unit_authority,
        "_SEGMENT_START_AUTHORITY",
        {segment: "".join(vector)},
    )
    monkeypatch.setattr(
        unit_authority,
        "_title_start_tags",
        lambda _description: {dollar_offset: "N"},
    )
    rows = unit_authority._segment_start_rows(description)
    dollar_row = next(row for row in rows if row[3] == dollar_offset)
    assert dollar_row[-1] == "whole_domain_denotation"


def test_title_positive_wins_a_shared_normalized_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    description = "years?-PERCENT"
    digest = hashlib.sha256(description.encode("utf-8")).hexdigest()
    year, percent = title_header_candidates(description)
    monkeypatch.setattr(
        unit_authority,
        "_TITLE_START_AUTHORITY",
        {
            (digest, *year): (
                None,
                "explicit_no_whole_domain_denotation",
                "test_year_defeat",
            ),
            (digest, *percent): (
                "percent",
                "whole_domain_denotation",
                "test_percent_output",
            ),
        },
    )
    assert unit_authority._title_start_tags(description) == {0: "W"}


def test_title_positive_survives_later_defeat_at_shared_normalized_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    description = "days/How many"
    digest = hashlib.sha256(description.encode("utf-8")).hexdigest()
    day, how_many = title_header_candidates(description)
    monkeypatch.setattr(
        unit_authority,
        "_TITLE_START_AUTHORITY",
        {
            (digest, *day): (
                "day",
                "whole_domain_denotation",
                "test_day_output",
            ),
            (digest, *how_many): (
                None,
                "explicit_no_whole_domain_denotation",
                "test_count_defeat",
            ),
        },
    )
    assert unit_authority._title_start_tags(description) == {0: "W"}


def test_cross_lf_separator_closure_applies_global_maximal_munch() -> None:
    script = (
        Path(__file__).parents[2]
        / "scripts"
        / "rebuild_amendment10_title_authority.py"
    )
    spec = importlib.util.spec_from_file_location(
        "amendment10_cross_lf", script
    )
    assert spec is not None and spec.loader is not None
    rebuild = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rebuild)

    raw, maximal = rebuild._cross_lf_compound_transition(
        "dollars per\nmonth or year"
    )
    assert Counter(candidate[0] for candidate in raw) == {
        "dollars_per_month_or_year": 1,
        "per_month_rate_phrase": 1,
    }
    assert tuple(candidate[0] for candidate in maximal) == (
        "dollars_per_month_or_year",
    )


def test_f1_suffix_input_hours_cannot_override_its_forced_defeat() -> None:
    script = (
        Path(__file__).parents[2]
        / "scripts"
        / "rebuild_amendment10_title_authority.py"
    )
    spec = importlib.util.spec_from_file_location(
        "amendment10_f1_suffix", script
    )
    assert spec is not None and spec.loader is not None
    rebuild = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rebuild)

    description = (
        "F1d. (In a typical week, how many hours [do you/does [he/she]] "
        "spend) Caring for or\nlooking after children? (CURRENTLY WORKING: "
        "Exclude hours providing care if this is\n[your/his/her] job.)\n"
        "The values for this variable represent the actual number of hours "
        "per week the Reference\nPerson spends caring for or looking after "
        "children."
    )
    candidates = rebuild.title_header_candidates(description)
    decisions = rebuild._adjudicate_context(
        {
            "interview_wave": 2017,
            "raw_field_id": "SYNTHETIC-F1D",
            "source_description": description,
        },
        candidates,
        {},
    )
    hour_rows = [
        (candidate, decision)
        for candidate, decision in zip(candidates, decisions, strict=True)
        if candidate[0] == "nominal_hour_token"
        and candidate[1] < len(rebuild._raw_title(description).encode("utf-8"))
    ]
    assert [decision for _candidate, decision in hour_rows] == [
        (
            "hour_per_week",
            "whole_domain_denotation",
            "typical_week_hours_title_denotation",
        ),
        (
            None,
            "explicit_no_whole_domain_denotation",
            "question_line_suffix_phrase_not_value_denotation",
        ),
    ]


@pytest.mark.parametrize("label_line", range(3, 9))
def test_structural_title_selector_can_start_on_physical_lines_three_through_eight(
    label_line: int,
) -> None:
    description = "\n".join(["Question"] * (label_line - 1) + ["Output--DAYS"])
    spans = unit_authority._title_selector_spans(description)
    assert len(spans) == 1
    assert description.count("\n", 0, spans[0][1]) + 1 == label_line
    assert unit_authority._raw_title(description) == description


@pytest.mark.parametrize(
    ("description", "label_line"),
    [
        (RAW_ER27217, 3),
        (RAW_ER49614, 7),
        (RAW_ER52049, 8),
    ],
)
def test_source_attested_late_selector_layouts_extend_the_exact_raw_header(
    description: str, label_line: int
) -> None:
    spans = unit_authority._title_selector_spans(description)
    assert spans
    assert description.count("\n", 0, spans[-1][1]) + 1 == label_line
    expected_header = description.rsplit("\nSee note", 1)[0]
    assert unit_authority._raw_title(description) == expected_header


@pytest.mark.parametrize(
    "description",
    [
        (
            "Household Food Security Category\n"
            "Raw score 0 -- High Food Security"
        ),
        (
            "Child Food Security Category\n"
            "Raw score 0-1 -- High or Marginal Food Security among Children"
        ),
        (
            "Question\n"
            "All three vars--BC41 YRS, BC41 MOS, and BC41 WKS--must be "
            "added together to calculate"
        ),
        (
            "Question\n"
            "automatic reinvestments--not including any IRAs? "
            "(NOTE EXCLUSION OF IRAS--DIFFERENT FROM\n"
            "1994)"
        ),
        "Question\nbased pensions or IRAs? [CHANGE FROM 1994--EXCLUDES IRAs]",
        (
            "Question\nemployer-based pensions or IRAs? "
            "[CHANGE FROM 1994--EXCLUDES IRAs]"
        ),
        (
            "Question\nin employer-based pensions or IRAs? "
            "[CHANGE FROM 1994--EXCLUDES IRAs]"
        ),
        "Question\n(CHANGE FROM 1994--EXCLUDES IRAs)",
        "Question\n(CHANGE FROM 1994--EXCLUDES I.R.A.s)",
        "Question\nFROM 1994--EXCLUDES IRAS)",
        "Question\n-----\nUPPERCASE BODY ROW",
        "Question\n-----\n-LABEL",
    ],
)
def test_closed_body_and_separator_lookalikes_are_not_title_selectors(
    description: str,
) -> None:
    assert unit_authority._title_selector_spans(description) == ()
    first_line_end = description.find("\n")
    question = description.rfind("?")
    question_line_end = (
        description.find("\n", question) if question >= 0 else -1
    )
    if question >= 0 and question_line_end < 0:
        question_line_end = len(description)
    expected_end = max(
        first_line_end,
        question_line_end if question >= 0 else first_line_end,
    )
    assert unit_authority._raw_title(description) == description[:expected_end]


def test_wrapped_number_of_times_is_count_valued_and_minutes_is_a_threshold() -> (
    None
):
    rows = title_header_candidate_table(
        [_row(2005, "ER27094", COMPILED, RAW_ER27094)]
    )[0]["candidate_adjudications"]
    assert any(
        row["typed_value_unit"] == "count"
        and row["adjudication"] == "whole_domain_denotation"
        for row in rows
    )
    assert any(
        row["family"] == "nominal_minute_token"
        and row["adjudication"] == "explicit_no_whole_domain_denotation"
        for row in rows
    )
    assert title_header_disposition(RAW_ER27094) == (
        "count",
        "derived_from_title_denotation",
    )


def test_nested_selector_components_are_deduplicated_and_response_visible() -> (
    None
):
    script = (
        Path(__file__).parents[2]
        / "scripts"
        / "rebuild_amendment10_title_authority.py"
    )
    spec = importlib.util.spec_from_file_location("amendment10_nested", script)
    assert spec is not None and spec.loader is not None
    rebuild = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rebuild)

    header = rebuild._raw_title(RAW_ER62267)
    components = rebuild._header_selector_occurrences(header)
    time_components = [
        row
        for row in components
        if normalize_description(row[3]).upper() == "TIME UNIT"
    ]
    assert len(time_components) == 1
    assert rebuild._header_response_selectors(header) == ("TIME UNIT",)

    nested_header = rebuild._raw_title(RAW_V22553)
    assert rebuild._header_response_selectors(nested_header) == (
        "TIME UNIT",
        "TIME UNIT",
    )
    assert (
        sum(
            normalize_description(component).upper() == "TIME UNIT"
            for _kind, _start, _end, component, _label, _terminal in (
                rebuild._header_selector_occurrences(nested_header)
            )
        )
        == 2
    )

    coordinate_header = rebuild._raw_title(RAW_ER60084)
    assert rebuild._header_output_labels(coordinate_header) == (
        (
            "month",
            coordinate_header.index("MONTH"),
            coordinate_header.index("MONTH") + len("MONTH"),
            "MONTH",
            "MONTH--SECOND MORTGAGE",
        ),
    )


def test_nested_singular_month_selector_is_an_explicit_calendar_defeat() -> (
    None
):
    rows = title_header_candidate_table(
        [_row(2015, "ER60084", INCOMPLETE, RAW_ER60084)]
    )[0]["candidate_adjudications"]
    assert rows
    assert all(
        row["adjudication"] == "explicit_no_whole_domain_denotation"
        for row in rows
    )
    assert any(
        row["reason"] == "singular_month_selector_is_calendar_coordinate"
        for row in rows
    )


@pytest.mark.parametrize(
    ("amount_description", "time_unit_description"),
    [
        (RAW_ER47459, RAW_ER47460),
        (RAW_ER66175, RAW_ER66176),
    ],
)
def test_overtime_amount_is_hours_but_paired_time_unit_is_not(
    amount_description: str, time_unit_description: str
) -> None:
    assert title_header_disposition(amount_description) == (
        "hour",
        "derived_from_title_denotation",
    )
    assert title_header_disposition(time_unit_description) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )


def test_dollars_worth_amount_is_dollars_but_paired_time_unit_is_not() -> None:
    assert title_header_disposition(RAW_ER3060) == (
        "united_states_dollar",
        "derived_from_title_denotation",
    )
    assert title_header_disposition(RAW_ER3061) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )


@pytest.mark.parametrize(
    ("description", "expected_unit", "in_dollars_is_positive"),
    [
        (RAW_ER15249, "united_states_dollar", True),
        (RAW_ER15250, None, False),
        (RAW_ER15251, "percent", False),
        (RAW_ER15252, None, False),
    ],
)
def test_pension_selector_siblings_select_only_their_response_arm(
    description: str,
    expected_unit: str | None,
    in_dollars_is_positive: bool,
) -> None:
    table = title_header_candidate_table(
        [_row(1999, "PENSION-SIBLING", COMPILED, description)]
    )[0]
    assert table["typed_value_unit"] == expected_unit
    in_dollars_rows = [
        row
        for row in table["candidate_adjudications"]
        if row["family"] == "in_dollars"
    ]
    assert len(in_dollars_rows) == 1
    assert (
        in_dollars_rows[0]["adjudication"] == "whole_domain_denotation"
    ) is in_dollars_is_positive


@pytest.mark.parametrize(
    "description",
    [
        "Number of year-to-year changes in county",
        "Number of year-to-year changes in state",
        "Number of year-to-year changes in region",
    ],
)
def test_year_to_year_change_titles_denote_counts_not_years(
    description: str,
) -> None:
    rows = title_header_candidate_table(
        [_row(1972, "YEAR-CHANGE", VALUE_CODE_ONLY, description)]
    )[0]["candidate_adjudications"]
    assert [
        (
            row["family"],
            row["typed_value_unit"],
            row["adjudication"],
            row["reason"],
        )
        for row in rows
    ] == [
        (
            "number_of_years",
            "count",
            "whole_domain_denotation",
            "count_of_changes_title_denotation",
        ),
        (
            "nominal_year_token",
            None,
            "explicit_no_whole_domain_denotation",
            "year_phrase_modifies_change_count",
        ),
    ]


def test_wrapped_month_body_defeats_preselector_experience_year() -> None:
    assert title_header_disposition(RAW_V22842) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )
    statement = description_statements(RAW_V22842)[0]
    assert statement.startswith(
        "The values for this variable in the range 001-997 represent "
    )
    assert statement_predicate(statement) is None
    assert field_unit(RAW_V22842) == (None, "no_statement_names_a_unit")


def test_typical_week_time_use_title_denotes_hours_per_week() -> None:
    rows = title_header_candidate_table(
        [_row(2017, "ER66716", COMPILED, RAW_ER66716)]
    )[0]["candidate_adjudications"]
    assert [
        (
            row["family"],
            row["typed_value_unit"],
            row["adjudication"],
            row["reason"],
        )
        for row in rows
    ] == [
        (
            "nominal_week_token",
            None,
            "explicit_no_whole_domain_denotation",
            "typical_week_rate_denominator",
        ),
        (
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "count_marker_subordinate_to_unit_noun",
        ),
        (
            "nominal_hour_token",
            "hour_per_week",
            "whole_domain_denotation",
            "typical_week_hours_title_denotation",
        ),
        (
            "nominal_day_token",
            None,
            "explicit_no_whole_domain_denotation",
            "first_question_coordinate_frequency_or_comparison_input",
        ),
        (
            "number_of_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ),
        (
            "hours_per_week",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ),
    ]
    assert field_unit(RAW_ER66716) == (
        "hour_per_week",
        "derived_from_title_denotation",
    )


def test_last_year_miles_title_denotes_miles_per_year() -> None:
    rows = title_header_candidate_table(
        [_row(1974, "V3520", COMPILED, RAW_V3520)]
    )[0]["candidate_adjudications"]
    assert [
        (
            row["family"],
            row["typed_value_unit"],
            row["adjudication"],
            row["reason"],
        )
        for row in rows
    ] == [
        (
            "nominal_year_token",
            None,
            "explicit_no_whole_domain_denotation",
            "last_year_rate_denominator",
        ),
        (
            "how_many_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "count_marker_subordinate_to_unit_noun",
        ),
        (
            "nominal_mile_token",
            "mile_per_year",
            "whole_domain_denotation",
            "last_year_miles_title_denotation",
        ),
        (
            "number_of_count_marker",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ),
        (
            "miles_per_year",
            None,
            "explicit_no_whole_domain_denotation",
            "delegated_to_primary_statement_grammar",
        ),
    ]
    assert field_unit(RAW_V3520) == (
        "mile_per_year",
        "derived_from_title_denotation",
    )


@pytest.mark.parametrize("description", [RAW_V11959, RAW_ER70826])
def test_highest_college_year_title_denotes_year(description: str) -> None:
    rows = title_header_candidate_table(
        [_row(2015, "COLLEGE-YEAR", COMPILED, description)]
    )[0]["candidate_adjudications"]
    actual = [
        (
            row["family"],
            row["typed_value_unit"],
            row["adjudication"],
            row["reason"],
        )
        for row in rows
    ]
    expected = [
        (
            "nominal_year_token",
            "year",
            "whole_domain_denotation",
            "highest_college_year_title_denotation",
        )
    ]
    if description == RAW_V11959:
        expected.append(
            (
                "number_of_years",
                None,
                "explicit_no_whole_domain_denotation",
                "delegated_to_primary_statement_grammar",
            )
        )
    assert actual == expected


@pytest.mark.parametrize("description", [RAW_ER64765, RAW_ER64904])
def test_school_years_outside_us_title_denotes_year(description: str) -> None:
    rows = title_header_candidate_table(
        [_row(2015, "SCHOOL-YEARS", COMPILED, description)]
    )[0]["candidate_adjudications"]
    assert [
        (
            row["family"],
            row["typed_value_unit"],
            row["adjudication"],
            row["reason"],
        )
        for row in rows
    ] == [
        (
            "nominal_year_token",
            "year",
            "whole_domain_denotation",
            "school_years_outside_us_title_denotation",
        )
    ]


@pytest.mark.parametrize("description", [RAW_ER64764, RAW_ER64907])
def test_adjacent_education_year_titles_remain_negative_controls(
    description: str,
) -> None:
    rows = title_header_candidate_table(
        [_row(2015, "EDUCATION-CONTROL", VALUE_CODE_ONLY, description)]
    )[0]["candidate_adjudications"]
    assert rows
    assert all(
        row["adjudication"] != "whole_domain_denotation" for row in rows
    )


def test_title_scanner_uses_utf8_offsets_and_ascii_case_and_boundaries() -> (
    None
):
    assert title_header_candidates("éHours") == (
        ("nominal_hour_token", 2, 7, "Hours"),
    )
    assert title_header_candidates("AHours") == ()
    assert title_header_disposition("éHours") == (
        None,
        "unadjudicated_title_candidate",
    )

    kelvin = title_header_candidates("How many weeKs")
    long_s = title_header_candidates("hourſ per week")
    assert not any(row[0] == "nominal_week_token" for row in kelvin)
    assert not any(row[0] == "hours_per_week" for row in long_s)


@pytest.mark.parametrize(
    ("description", "unit"),
    [
        (
            "D33, E14. About how many miles was it to where you work(ed)? "
            "(One way) (1969 questions)",
            "mile",
        ),
        (
            "C73. How many hours of overtime did you work on that job in 1993?",
            "hour",
        ),
        ("D61. How much work did she miss?--DAYS", "day"),
        ("C3. How long have you been looking for work?--MONTHS", "month"),
    ],
)
def test_generic_question_titles_participate_in_unit_derivation(
    description: str, unit: str
) -> None:
    assert title_header_disposition(description) == (
        unit,
        "derived_from_title_denotation",
    )
    assert field_unit(description) == (unit, "derived_from_title_denotation")


@pytest.mark.parametrize(
    "description",
    [
        (
            "G10. Are you and your Wife now doing anything to limit the number "
            "of children you will\nhave? (1970 question)"
        ),
        (
            "M5. Have you had a number of different kinds of jobs, or have you "
            "mostly worked in the\nsame occupation you started in, or what?"
        ),
        (
            "1995 Interview Number of the First Other Family Unit Sharing the "
            "Household with This\nFamily\nValues for this variable represent the "
            "actual 1995 ID number of the first other family\nliving with this one."
        ),
        (
            "2019 Interview Number of the Second Other Family Unit Sharing the "
            "Household with This\nFamily\nValues for this variable represent the "
            "actual 2019 ID number of the second other family\nliving with this one."
        ),
    ],
)
def test_number_phrases_in_yes_no_and_identifier_titles_are_defeated(
    description: str,
) -> None:
    table = title_header_candidate_table(
        [_row(2000, "NUMBER-DEFEAT", COMPILED, description)]
    )[0]
    assert table["candidate_adjudications"]
    assert all(
        row["adjudication"] == "explicit_no_whole_domain_denotation"
        for row in table["candidate_adjudications"]
    )
    assert title_header_disposition(description) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )


@pytest.mark.parametrize(
    ("description", "expected_unit"),
    [
        (
            "DE45. How many hours did that overtime amount to in (that period "
            "during) 2008?--TIME UNIT\nFOR JOB 3",
            None,
        ),
        (
            "D40. (In addition to the weeks and hours worked you have just told "
            "us about,) did you\n(HEAD) have an extra job or other way of making "
            "money in 1983?\nD46. Did you have any other extra jobs in 1983?\n"
            "The values for this variable represent the total number of extra "
            "jobs (1-7) that Head had.",
            "count",
        ),
        *(
            (description, None)
            for description in CURRENT_MAIN_JOB_HOUR_INPUT_CONTEXTS
        ),
    ],
)
def test_time_unit_and_prior_hours_title_inputs_are_not_output_units(
    description: str, expected_unit: str | None
) -> None:
    table = title_header_candidate_table(
        [_row(2009, "HOUR-DEFEAT", COMPILED, description)]
    )[0]
    assert all(
        row["adjudication"] == "explicit_no_whole_domain_denotation"
        for row in table["candidate_adjudications"]
    )
    assert field_unit(description)[0] == expected_unit


def test_current_main_job_false_hour_cohort_covers_all_six_fields() -> None:
    assert len(CURRENT_MAIN_JOB_HOUR_INPUT_FIELDS) == 6
    assert len(set(CURRENT_MAIN_JOB_HOUR_INPUT_FIELDS)) == 6
    assert len(CURRENT_MAIN_JOB_HOUR_INPUT_CONTEXTS) == 3
    for description in CURRENT_MAIN_JOB_HOUR_INPUT_CONTEXTS:
        rows = title_header_candidate_table(
            [_row(2015, "CURRENT-MAIN-JOB", COMPILED, description)]
        )[0]["candidate_adjudications"]
        hour_rows = [
            row for row in rows if row["family"] == "nominal_hour_token"
        ]
        assert hour_rows
        assert all(
            row["adjudication"] == "explicit_no_whole_domain_denotation"
            for row in hour_rows
        )


@pytest.mark.parametrize(
    ("description", "unit", "negative_reason"),
    [
        (
            "G14. How many of these years did she work full time for most of "
            "the year?",
            "year",
            "period_phrase_is_reference_coverage",
        ),
        (
            "1969 hours of nonleisure comparable to 1967 hours of nonleisure\n"
            "This variable is comparable to 1967 variable since it doesn't "
            "include travel to work time.\nV1508 (Total nonleisure in 1969) -\n"
            "V1146 (Head's travel to work time) -\n"
            "V1152 (Wife's travel to work time)",
            "hour",
            "hour_phrase_modifies_included_or_reference_input",
        ),
    ],
)
def test_repeated_period_inputs_do_not_become_second_title_denotations(
    description: str, unit: str, negative_reason: str
) -> None:
    rows = title_header_candidate_table(
        [_row(1974, "REPEATED-PERIOD", COMPILED, description)]
    )[0]["candidate_adjudications"]
    assert (
        sum(row["adjudication"] == "whole_domain_denotation" for row in rows)
        == 1
    )
    assert any(row["reason"] == negative_reason for row in rows)
    assert field_unit(description) == (unit, "derived_from_title_denotation")


@pytest.mark.parametrize(
    ("title_unit", "statement_unit", "family"),
    [
        ("hour_per_week", "hour", "hours_per_week"),
        ("hour_per_year", "hour", "hours_per_year"),
        ("mile_per_year", "mile", "miles_per_year"),
        (
            "united_states_dollar_per_hour",
            "united_states_dollar",
            "dollars_per_hour",
        ),
        (
            "united_states_dollar_per_week",
            "united_states_dollar",
            "dollars_per_week",
        ),
    ],
)
def test_only_supported_exact_title_rates_refine_bare_statement_units(
    monkeypatch: pytest.MonkeyPatch,
    title_unit: str,
    statement_unit: str,
    family: str,
) -> None:
    monkeypatch.setattr(
        unit_authority,
        "title_header_disposition",
        lambda _description: (title_unit, "derived_from_title_denotation"),
    )
    monkeypatch.setattr(
        unit_authority,
        "_title_candidate_rows",
        lambda _description: (
            (
                family,
                0,
                1,
                "x",
                title_unit,
                "whole_domain_denotation",
                "test_exact_refinement",
            ),
        ),
    )
    monkeypatch.setattr(
        unit_authority,
        "description_statements",
        lambda _description: ("statement",),
    )
    monkeypatch.setattr(
        unit_authority,
        "statement_disposition",
        lambda _statement: (statement_unit, "unit_naming_clause"),
    )
    assert field_unit("synthetic exact refinement") == (
        title_unit,
        "derived_from_title_denotation",
    )


def test_exact_month_body_defeats_a_conflicting_experience_year() -> None:
    description = (
        "B23. How many years' experience do you (HEAD) have altogether "
        "with your present employer?\nThe values for this variable "
        "represent the actual number of monthsHead has worked for the\n"
        "present employer."
    )
    assert title_header_disposition(description) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )
    assert field_unit(description) == (
        "month",
        "derived_from_denotation_statement",
    )


def test_title_rebuilder_rejects_distinct_positive_units_in_either_order() -> (
    None
):
    script = (
        Path(__file__).parents[2]
        / "scripts"
        / "rebuild_amendment10_title_authority.py"
    )
    spec = importlib.util.spec_from_file_location(
        "amendment10_rebuild", script
    )
    assert spec is not None and spec.loader is not None
    rebuild = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rebuild)

    description = "Hours and days"
    sha = hashlib.sha256(description.encode("utf-8")).hexdigest()
    candidates = (
        ("nominal_hour_token", 0, 5, "Hours"),
        ("nominal_day_token", 10, 14, "days"),
    )
    old_rows = {
        sha: [
            (
                sha,
                description,
                family,
                start,
                end,
                spelling,
                unit,
                "whole_domain_denotation",
                "synthetic_independent_positive",
                1968,
                "SYNTHETIC",
            )
            for (family, start, end, spelling), unit in zip(
                candidates, ("hour", "day"), strict=True
            )
        ]
    }
    row = {
        "interview_wave": 1968,
        "raw_field_id": "SYNTHETIC",
        "source_description": description,
    }
    for ordered in (candidates, tuple(reversed(candidates))):
        with pytest.raises(ValueError, match="inherited title conflict"):
            rebuild._adjudicate_context(row, ordered, old_rows)


def test_title_table_keeps_every_field_and_exact_raw_domain_groundings() -> (
    None
):
    rows = [
        _row(1968, "V31", COMPILED, RAW_V31),
        _row(1968, "V47", COMPILED, TITLE_WITNESSES[0][0]),
    ]
    table = title_header_candidate_table(rows)
    assert len(table) == 2
    assert table[0]["candidate_count"] == 8
    assert table[0]["typed_value_unit"] is None
    assert table[0]["raw_candidate_domain"] == RAW_V31
    assert table[0]["raw_candidate_domain_byte_count"] == len(
        RAW_V31.encode("utf-8")
    )
    assert table[0]["candidate_offsets"] == (
        "zero-based UTF-8 byte offsets in raw_candidate_domain"
    )
    assert table[0]["bounded_context_header"] == "Annual food standard (Needs)"
    assert (
        table[0]["raw_candidate_domain_sha256"]
        == hashlib.sha256(RAW_V31.encode("utf-8")).hexdigest()
    )
    assert {row["reason"] for row in table[0]["candidate_adjudications"]} == {
        "input_table_or_subrange_not_field_denotation"
    }
    assert table[1]["candidate_count"] == 1
    assert table[1]["typed_value_unit"] == "hour"
    assert table[1]["candidate_adjudications"][0]["adjudication"] == (
        "whole_domain_denotation"
    )


def test_unfrozen_title_mutation_fails_closed() -> None:
    description = "Head's annual hours working for MONEY"
    assert title_header_candidates(description)
    assert title_header_disposition(description) == (
        None,
        "unadjudicated_title_candidate",
    )
    assert field_unit(description) == (None, "defeated_title_denotation")


@pytest.mark.parametrize(
    "description",
    [
        "Bkt. V335 Total 1967 Family Hours of Work (Work for money plus unpaid work)",
        "P13. What amount or percent of pay are you required to contribute?--AMOUNT",
    ],
)
def test_reference_and_alternative_title_phrases_are_explicit_defeats(
    description: str,
) -> None:
    assert title_header_candidates(description)
    assert title_header_disposition(description) == (
        None,
        "title_clause_explicitly_non_whole_domain",
    )


def test_weekly_title_refines_a_subordinate_bare_hour_statement() -> None:
    description = (
        "D69. On the average, how many hours a week did you work at your extra job(s)?\n"
        "Actual number of hours"
    )
    assert field_unit(description) == (
        "hour_per_week",
        "derived_from_title_denotation",
    )


@pytest.mark.parametrize("description", [RAW_V2470, RAW_V3694, RAW_V9378])
def test_complete_raw_food_family_keeps_context_and_derives_dollars(
    description: str,
) -> None:
    statements = description_statements(description)
    assert statements
    assert statement_disposition(statements[0]) == (
        None,
        "no_unit_naming_clause",
    )
    assert any(
        statement_disposition(statement)
        == ("united_states_dollar", "unit_naming_clause")
        for statement in statements[1:]
    )
    expected_reason = (
        "derived_from_title_denotation"
        if description.startswith("Weekly Food Needs\n")
        else "derived_from_denotation_statement"
    )
    assert field_unit(description) == ("united_states_dollar", expected_reason)


def test_complete_raw_needs_note_denotes_1967_dollars() -> None:
    statement = (
        "this variable is not adjusted for inflation (it is in 1967 "
        "dollars), nor is it exactly comparable to the official poverty "
        "standard; such changes are left to users."
    )
    assert description_statements(RAW_V21488) == (statement,)
    assert statement_disposition(statement) == (
        "united_states_dollar",
        "unit_naming_clause",
    )
    assert field_unit(RAW_V21488) == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


@pytest.mark.parametrize("description", [RAW_ER12067, RAW_ER12079])
def test_complete_raw_1997_income_note_denotes_1996_dollars(
    description: str,
) -> None:
    assert any(
        statement_disposition(statement)
        == ("united_states_dollar", "unit_naming_clause")
        for statement in description_statements(description)
    )
    assert field_unit(description) == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


def test_complete_raw_month_code_denotes_months() -> None:
    assert description_statements(RAW_ER3062) == (
        "Months are coded below with January=1, February=2, etc.",
    )
    assert field_unit(RAW_ER3062) == (
        "month",
        "derived_from_denotation_statement",
    )


def test_complete_raw_compound_month_day_code_fails_closed() -> None:
    statement = (
        "The first 2 digits represent the month, the last 2 digits represent "
        "the day."
    )
    assert description_statements(RAW_ER2005) == (statement,)
    assert statement_disposition(statement) == (None, "defeating_clause")
    assert field_unit(RAW_ER2005) == (
        None,
        "defeated_denotation_statement",
    )


@pytest.mark.parametrize("description", ROUND2_RAW_DESCRIPTIONS)
def test_round2_raw_descriptions_have_total_exact_start_cover(
    description: str,
) -> None:
    partition = denotation_candidate_start_partition(description)
    assert set(partition) == {
        "whole_domain_denotation",
        "explicit_no_whole_domain_denotation",
        "explicit_no_denotation",
        "unadjudicated_start",
    }
    assert sum(partition.values()) == denotation_candidate_start_count(
        description
    )
    assert partition["unadjudicated_start"] == 0
    assert denotation_candidate_unselected_count(description) == 0
    assert denotation_candidate_overselected_count(description) == 0


def test_every_actual_denotation_has_one_full_span_clause() -> None:
    clause_map = dict(ACTUAL_CLAUSE_TABLE)
    expected = set(ACTUAL_CANDIDATES) - ACTUAL_NO_DENOTATION_CANDIDATES
    assert set(clause_map) == expected
    for candidate in expected:
        assert statement_disposition(candidate)[1] != "no_unit_naming_clause"


# --------------------------------------------------------------------------
# Stage 2 — whole-domain predicate
# --------------------------------------------------------------------------


def test_range_scoped_statement_has_no_whole_domain_predicate() -> None:
    text = (
        "The values for this variable in the range 00001-99998 represent "
        "the amount of child support received in whole dollars."
    )
    assert extract_statements(text) == (text,)
    assert statement_predicate(text) is None
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


def test_values_in_range_family_is_selected_but_subrange_scoped() -> None:
    text = "Values in the range 001-998 represent number of hours per year."
    assert extract_statements(text) == (text,)
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


def test_whole_domain_predicate_strips_subject_and_verb() -> None:
    assert statement_predicate(DOLLARS) == "dollars and cents."
    assert (
        statement_predicate("This variable represents whole dollars.")
        == "whole dollars."
    )


@pytest.mark.parametrize(
    "text",
    [
        "Coded value represents the last two digits of the year.",
        "The code value represents the actual number of persons in the FU.",
        (
            "The code values for this variable represent the actual number "
            "of miles per year."
        ),
        (
            "The range of values for this variable represents actual age "
            "in years."
        ),
        "The values in this variable refer to the state and county.",
        "This four digit variable represents the month and day.",
        "The values for this variable indicate the year of graduation.",
    ],
)
def test_audited_direct_denotation_openers_are_selected(text: str) -> None:
    assert extract_statements(text) == (text,)
    assert statement_predicate(text) is not None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "This variable contains the year of data collection.",
            "year",
        ),
        (
            "The actual number of minutes taken by the interviewer to "
            "administer the questionnaire is coded here.",
            "minute",
        ),
        (
            "This is the number of businesses owned by either the Head, "
            'the Wife/"Wife", or both.',
            "count",
        ),
        ("The values are in 1967 dollars.", "united_states_dollar"),
    ],
)
def test_coded_and_value_subject_families_name_units(
    text: str,
    expected: str,
) -> None:
    assert statement_disposition(text) == (
        expected,
        "unit_naming_clause",
    )


@pytest.mark.parametrize(
    "text",
    [
        "The data coded here represent income in whole dollars.",
        "The month coded here is that of the most recent move.",
        "The values for this variable sum the total number of reports.",
    ],
)
def test_unenumerated_longer_source_like_predicates_defeat(text: str) -> None:
    assert statement_disposition(text) == (None, "defeating_clause")


@pytest.mark.parametrize(
    "text",
    [
        "This variable contains the last two digits of the year.",
        "This variable contains the total number of records.",
        "This variable indicates whether a record exists.",
        "This variable refers to the first mention of ownership.",
        "The values in this variable refer to the state and county.",
        "The condition of the car in best shape is coded here",
        (
            "The actual 1985 sequence number (V30490) of the individual who "
            "produced the income is coded here."
        ),
    ],
)
def test_explicit_coded_and_direct_defeaters(text: str) -> None:
    assert statement_disposition(text) == (None, "defeating_clause")


def test_include_is_selected_but_explicitly_not_a_denotation() -> None:
    text = "The values for this variable include all children living here."
    assert extract_statements(text) == (text,)
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


@pytest.mark.parametrize(
    "text",
    [
        "Values in the range 0001-9998 denote interview identifiers.",
        "the value here represents a weighted average hourly wage.",
        "The negative values indicate a loss in whole dollars.",
    ],
)
def test_audited_subrange_families_cannot_establish_a_unit(text: str) -> None:
    assert extract_statements(text) == (text,)
    assert statement_disposition(text) == (
        None,
        "not_a_whole_domain_denotation",
    )


# --------------------------------------------------------------------------
# Stage 3 — the clause table
# --------------------------------------------------------------------------


def test_maximal_munch_prefers_the_longer_nested_clause() -> None:
    assert statement_disposition(PER_HOUR) == (
        "united_states_dollar_per_hour",
        "unit_naming_clause",
    )
    assert statement_disposition(DOLLARS) == (
        "united_states_dollar",
        "unit_naming_clause",
    )


def test_two_distinct_units_in_one_statement_fail_closed() -> None:
    text = (
        "The values for this variable represent dollars and cents per hour; "
        "if salary is given as an annual figure, it is divided by 2000 "
        "hours per year; if weekly, by 40 hours per week."
    )
    assert statement_disposition(text) == (None, "conflicting_unit_clauses")


def test_a_defeating_clause_beats_a_unit_clause() -> None:
    text = (
        "The values for this variable represent the actual marginal tax "
        "rate based on this person's percent proration, taxable income, "
        "number of exemptions, and tax table used."
    )
    assert statement_disposition(text) == (None, "defeating_clause")


def test_a_statement_naming_no_unit_fails_closed() -> None:
    text = (
        "The values for this variable represent overall income profits or "
        "losses."
    )
    assert statement_disposition(text) == (None, "no_unit_naming_clause")


def test_administration_does_not_match_a_ratio_defeater() -> None:
    text = (
        "The values for this variable represent the Veterans Administration "
        "Pension income of all other FU members in the FU in 1992 in whole "
        "dollars."
    )
    assert statement_disposition(text)[0] == "united_states_dollar"


def test_a_per_hour_tail_outranks_the_bare_money_clause() -> None:
    text = "This variable represents dollar and cents amount per hour."
    assert statement_disposition(text) == (
        "united_states_dollar_per_hour",
        "unit_naming_clause",
    )


@pytest.mark.parametrize(
    "predicate",
    [
        "dollars and cents amount per hour",
        "nominal whole dollars",
        "whole dollars nominal amount",
        "whole dollars / hour",
        "whole dollars\N{NO-BREAK SPACE}per hour",
        "whole dollars per hour",
        "number of hours per day",
        "number of miles per week",
        "number of persons per acre",
        "number of hours (0001-2080) per day",
        "whole dollars (nominal) per hour",
    ],
)
def test_every_unenumerated_longer_phrase_fails_closed(
    predicate: str,
) -> None:
    text = f"This variable represents {predicate}."
    assert statement_disposition(text) == (None, "defeating_clause")


def test_explicit_and_general_plural_defeat_is_one_full_span_hit() -> None:
    predicate = "dollars and cents amount per hour"
    assert clause_occurrences(predicate) == ((0, len(predicate), NO_UNIT),)


def test_every_authorized_positive_defeats_unknown_left_and_right_extensions() -> (
    None
):
    positive_rows = [
        (predicate, unit)
        for predicate, unit, reason in PREDICATE_AUTHORITY
        if reason == "unit_naming_clause"
    ]
    assert len(positive_rows) == 1_534
    for predicate, unit in positive_rows:
        assert unit is not None
        assert unit in {
            found for _start, _end, found in clause_occurrences(predicate)
        }
        for extension in (f"unknown {predicate}", f"{predicate} unknown"):
            units = {
                found for _start, _end, found in clause_occurrences(extension)
            }
            if predicate.startswith(
                ("CODE ", "Code ", "Coded ", "ENTER ", "RECORD ")
            ):
                # Direct coding predicates are not lexical clause rows, so
                # an unknown extension may have no clause hit at all.  It
                # still cannot inherit any positive unit.
                assert units in (set(), {NO_UNIT})
            else:
                assert units == {NO_UNIT}
            assert not set(UNIT_VOCABULARY) & units


@pytest.mark.parametrize(
    ("predicate", "unit"),
    [
        ("dollars and cents per hour", "united_states_dollar_per_hour"),
        (
            "dollar and cents amount per hour",
            "united_states_dollar_per_hour",
        ),
        ("number of hours per week", "hour_per_week"),
        ("hours per week", "hour_per_week"),
        ("hours per year", "hour_per_year"),
        (
            "number of hours (0001-2080) per year",
            "hour_per_year",
        ),
        ("number of miles per year", "mile_per_year"),
    ],
)
def test_enumerated_ratio_phrase_survives(
    predicate: str,
    unit: str,
) -> None:
    text = f"This variable represents {predicate}."
    assert statement_disposition(text) == (unit, "unit_naming_clause")


def test_a_density_is_defeated_rather_than_counted() -> None:
    text = (
        "The values for this variable represent the number of persons per "
        "room with one implied decimal place; e.g., a value of 20 here "
        "represents 2.0 persons per room."
    )
    assert statement_disposition(text) == (None, "defeating_clause")


@pytest.mark.parametrize(
    ("statement", "unit"),
    [
        ("Actual dollar and cents per hour", "united_states_dollar_per_hour"),
        ("Actual number of dollars", "united_states_dollar"),
        (
            "Actual expenditure in hundreds of dollars",
            "hundreds_of_united_states_dollars",
        ),
        ("Actual dollars per week", "united_states_dollar_per_week"),
        ("Actual hours worked per week", "hour_per_week"),
        ("Actual number of hours per year", "hour_per_year"),
        ("Actual number in FU", "count"),
        ("Actual number in Family Unit", "count"),
        ("Actual number in family unit", "count"),
        ("Actual year", "year"),
    ],
)
def test_supplemental_actual_clauses_resolve(
    statement: str,
    unit: str,
) -> None:
    assert statement_disposition(statement) == (unit, "unit_naming_clause")


@pytest.mark.parametrize(
    "statement",
    [
        "Actual interview number was coded: 0001-6620)",
        "Actual Minus Required Rooms for Family",
        "Actual minus required rooms for family",
        "Actual score:",
    ],
)
def test_supplemental_actual_defeaters_resolve(statement: str) -> None:
    assert statement_disposition(statement) == (None, "defeating_clause")


def test_clause_occurrences_drop_only_strictly_contained_matches() -> None:
    hits = clause_occurrences("dollars and cents per hour")
    assert [unit for _start, _end, unit in hits] == [
        "united_states_dollar_per_hour"
    ]


def test_longest_non_nested_same_disposition_clause_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predicate = "total weeks and weeks worked"
    # A registered conflict leaves nonnested lexical rows to the tie-break;
    # an unregistered complete phrase would instead fail closed first.
    monkeypatch.setitem(
        unit_authority._PREDICATE_AUTHORITY,
        predicate,
        (None, "conflicting_unit_clauses"),
    )
    hits = clause_occurrences(predicate)
    assert hits == ((16, 28, "week"),)


def test_clause_matching_is_invariant_to_table_enumeration_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    predicate = "number of hours per day"
    expected = clause_occurrences(predicate)
    monkeypatch.setattr(
        "populace_dynamics.data.psid_unit_authority.CLAUSE_TABLE",
        tuple(reversed(CLAUSE_TABLE)),
    )
    assert set(clause_occurrences(predicate)) == set(expected)


def test_every_clause_unit_is_in_the_closed_vocabulary() -> None:
    for _clause, unit in CLAUSE_TABLE:
        assert unit == NO_UNIT or unit in UNIT_VOCABULARY


def test_clause_table_has_no_duplicate_clause() -> None:
    clauses = [clause for clause, _unit in CLAUSE_TABLE]
    assert len(clauses) == len(set(clauses))


# --------------------------------------------------------------------------
# Field disposition
# --------------------------------------------------------------------------


def test_field_with_no_statement_has_no_unit() -> None:
    assert field_unit("House value") == (None, "no_denotation_statement")
    assert field_unit(None) == (None, "no_denotation_statement")


def test_field_takes_the_single_unit_its_statements_name() -> None:
    assert field_unit(DOLLARS) == (
        "united_states_dollar",
        "derived_from_denotation_statement",
    )


def test_field_with_two_distinct_statement_units_fails_closed() -> None:
    assert field_unit(f"{DOLLARS}\n{HOURS}") == (
        None,
        "conflicting_statement_units",
    )


def test_primary_and_residual_selectors_union_and_conflict() -> None:
    description = (
        "The values for this variable represent the actual number of years.\n"
        "Actual number of months"
    )
    assert field_unit(description) == (None, "conflicting_statement_units")


def test_defeated_statement_blocks_a_positive_statement() -> None:
    defeated = (
        "The values for this variable represent the number of persons per "
        "room."
    )
    for text in (f"{DOLLARS} {defeated}", f"{defeated} {DOLLARS}"):
        assert field_unit(text) == (None, "defeated_denotation_statement")


def test_unadjudicated_actual_candidate_blocks_a_positive_statement() -> None:
    text = f"{DOLLARS}\nActual furlongs per fortnight"
    assert field_unit(text) == (None, "defeated_denotation_statement")


def test_conflicting_statement_blocks_a_positive_statement() -> None:
    conflict = (
        "The values for this variable represent dollars and cents per hour; "
        "if salary is given as an annual figure, it is divided by 2000 hours "
        "per year; if weekly, by 40 hours per week."
    )
    assert statement_disposition(conflict) == (
        None,
        "conflicting_unit_clauses",
    )
    assert field_unit(f"{DOLLARS} {conflict}") == (
        None,
        "defeated_denotation_statement",
    )


def test_field_whose_only_statement_names_nothing_fails_closed() -> None:
    text = "The values for this variable represent the actual age of the Head."
    assert field_unit(text) == (None, "no_statement_names_a_unit")


def test_line_wrapped_statement_still_matches() -> None:
    wrapped = "The values for this variable represent dollars\nand cents."
    assert field_unit(wrapped)[0] == "united_states_dollar"


# --------------------------------------------------------------------------
# The successor terminal function
# --------------------------------------------------------------------------


def test_compiled_field_without_a_unit_moves_to_incomplete() -> None:
    assert successor_terminal(COMPILED, None) == (INCOMPLETE, True)
    assert successor_terminal(PARTIAL_RANGE, None) == (INCOMPLETE, True)


def test_compiled_field_with_a_unit_does_not_move() -> None:
    for terminal in COMPILED_TERMINALS:
        assert successor_terminal(terminal, "united_states_dollar") == (
            terminal,
            False,
        )


@pytest.mark.parametrize(
    "terminal",
    [
        VALUE_CODE_ONLY,
        RANGE_UNESTABLISHED,
        "nonnumeric_source_field_outside_numeric_grammar",
        CONFLICTING,
        UNSUPPORTED,
        INCOMPLETE,
    ],
)
def test_precedence_keeps_every_noncompiled_terminal_fixed(
    terminal: str,
) -> None:
    assert successor_terminal(terminal, None) == (terminal, False)
    assert successor_terminal(terminal, "week") == (terminal, False)


def test_terminal_order_is_the_ten_ratified_terminals() -> None:
    assert len(TERMINAL_ORDER) == 10
    assert len(set(TERMINAL_ORDER)) == 10
    assert COMPILED_TERMINALS <= set(TERMINAL_ORDER)
    assert set(FAILURE_TERMINALS) <= set(TERMINAL_ORDER)


# --------------------------------------------------------------------------
# Denominator partition
# --------------------------------------------------------------------------


def test_artifact_partition_covers_the_whole_denominator() -> None:
    assert sum(size for _name, size in ARTIFACT_PARTITION) == 89_599
    assert artifact_of_position(0) == ARTIFACT_PARTITION[0][0]
    assert artifact_of_position(3_867) == ARTIFACT_PARTITION[0][0]
    assert artifact_of_position(3_868) == ARTIFACT_PARTITION[1][0]
    assert artifact_of_position(89_598) == ARTIFACT_PARTITION[-1][0]
    with pytest.raises(ValueError):
        artifact_of_position(89_599)


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------


def _row(wave: int, field: str, status: str, description: str | None) -> dict:
    return {
        "interview_wave": wave,
        "raw_field_id": field,
        "derivation_status": status,
        "resolution_reason": "structural_literal_domain",
        "source_description": description,
    }


def test_successor_census_moves_only_unitless_compiled_fields() -> None:
    rows = [
        _row(1968, "A", COMPILED, DOLLARS),
        _row(1968, "B", COMPILED, "House value"),
        _row(1968, "C", UNSUPPORTED, "House value"),
        _row(1968, "D", VALUE_CODE_ONLY, "House value"),
    ]
    census = successor_census(rows)
    counts = {
        row["derivation_status"]: row["field_count"]
        for row in census["count_rows"]
    }
    assert counts[COMPILED] == 1
    assert counts[INCOMPLETE] == 1
    assert counts[UNSUPPORTED] == 1
    assert counts[VALUE_CODE_ONLY] == 1
    assert census["movement_row_count"] == 1
    moved = census["movement_rows"][0]
    assert moved["raw_field_id"] == "B"
    assert moved["resolution_reason"] == UNIT_ABSENT_RESOLUTION_REASON
    assert moved["unit_absence_reason"] == "no_denotation_statement"
    assert census["field_count"] == 4
    assert census["denominator_sha256"] == canonical_sha256(
        [[1968, "A"], [1968, "B"], [1968, "C"], [1968, "D"]]
    )


def test_ordered_assignment_binds_a_retained_resolution_reason() -> None:
    row = _row(1968, "A", COMPILED, DOLLARS)
    row["resolution_reason"] = "first_retained_reason"
    first = successor_census([row])
    changed_row = dict(row)
    changed_row["resolution_reason"] = "changed_retained_reason"
    changed = successor_census([changed_row])

    assert first["denominator_sha256"] == changed["denominator_sha256"]
    assert first["count_array_sha256"] == changed["count_array_sha256"]
    assert first["ordered_assignment_sha256"] == canonical_sha256(
        [(1968, "A", COMPILED, "first_retained_reason")]
    )
    assert (
        first["ordered_assignment_sha256"]
        != (changed["ordered_assignment_sha256"])
    )


def test_successor_census_rejects_a_duplicate_field_key() -> None:
    rows = [
        _row(1968, "A", COMPILED, None),
        _row(1968, "A", COMPILED, None),
    ]
    with pytest.raises(ValueError, match="duplicate field key"):
        successor_census(rows)


def test_successor_census_rejects_an_unknown_terminal() -> None:
    with pytest.raises(ValueError, match="unknown ratified terminal"):
        successor_census([_row(1968, "A", "made_up", None)])


def test_successor_census_rejects_a_short_row() -> None:
    row = _row(1968, "A", COMPILED, None)
    del row["resolution_reason"]
    with pytest.raises(ValueError, match="unexpected keys"):
        successor_census([row])


def test_successor_census_rejects_an_extra_member() -> None:
    row = _row(1968, "A", COMPILED, None)
    row["extra"] = "not canonical"
    with pytest.raises(ValueError, match="unexpected keys"):
        successor_census([row])


@pytest.mark.parametrize(
    ("member", "value", "message"),
    [
        ("interview_wave", True, "JSON integer"),
        ("raw_field_id", 1, "JSON string"),
        ("derivation_status", 1, "JSON string"),
        ("resolution_reason", None, "JSON string"),
        ("source_description", 1, "JSON string or null"),
    ],
)
def test_successor_census_rejects_noncanonical_member_types(
    member: str,
    value: object,
    message: str,
) -> None:
    row = _row(1968, "A", COMPILED, None)
    row[member] = value
    with pytest.raises(ValueError, match=message):
        successor_census([row])


def test_failure_reason_rows_follow_precedence_then_reason() -> None:
    rows = failure_reason_rows(
        [
            (1970, "B", INCOMPLETE, "zeta"),
            (1969, "A", UNSUPPORTED, "beta"),
            (1971, "C", INCOMPLETE, "alpha"),
            (1972, "D", CONFLICTING, "gamma"),
            (1973, "E", COMPILED, "not-a-failure"),
        ]
    )
    assert [
        (row["derivation_status"], row["resolution_reason"]) for row in rows
    ] == [
        (CONFLICTING, "gamma"),
        (UNSUPPORTED, "beta"),
        (INCOMPLETE, "alpha"),
        (INCOMPLETE, "zeta"),
    ]
    assert rows[2]["field_keys"] == [[1971, "C"]]


def test_statement_table_is_sorted_and_carries_a_witness() -> None:
    rows = [
        _row(1968, "B", COMPILED, HOURS),
        _row(1968, "A", COMPILED, f"{DOLLARS} {HOURS}"),
    ]
    table = statement_table(rows)
    assert [row["statement"] for row in table] == sorted({DOLLARS, HOURS})
    by_statement = {row["statement"]: row for row in table}
    assert by_statement[HOURS]["field_count"] == 2
    assert by_statement[HOURS]["witness_field_key"] == [1968, "B"]
    assert by_statement[DOLLARS]["typed_value_unit"] == (
        "united_states_dollar"
    )


def test_actual_candidate_table_is_sorted_and_carries_adjudication() -> None:
    rows = [
        _row(1968, "B", COMPILED, "Actual number of weeks"),
        _row(1968, "A", COMPILED, "Actual number of weeks"),
        _row(1968, "C", COMPILED, "Actual made-up measure"),
    ]
    table = actual_candidate_table(rows)
    assert [row["candidate"] for row in table] == sorted(
        {"Actual number of weeks", "Actual made-up measure"}
    )
    by_candidate = {row["candidate"]: row for row in table}
    assert by_candidate["Actual number of weeks"]["field_count"] == 2
    assert by_candidate["Actual number of weeks"]["witness_field_key"] == [
        1968,
        "B",
    ]
    assert by_candidate["Actual made-up measure"]["adjudication"] == (
        "unadjudicated_no_denotation"
    )


def test_coding_candidate_table_covers_every_potential_coding_start() -> None:
    rows = [
        _row(1968, "A", COMPILED, RAW_V100),
        _row(1968, "B", COMPILED, RAW_V229),
    ]
    table = coding_candidate_table(rows)
    assert [row["candidate"] for row in table] == sorted(
        {
            "Code actual number of MINUTES (e.g.",
            "Code dollars and cents per hour.)",
        }
    )
    assert all(
        row["adjudication"] == "whole_domain_denotation" for row in table
    )
    assert all(row["selected_statement"] is not None for row in table)
    assert all(
        row["occurrence_count"] == row["field_count"] == 1 for row in table
    )


def test_denotation_candidate_table_dispositions_every_contextual_start() -> (
    None
):
    rows = [_row(1976, "V4742", COMPILED, RAW_V4742)]
    table = denotation_candidate_table(rows)
    assert len(table) == denotation_candidate_start_count(RAW_V4742)
    assert all(
        set(row)
        == {
            "segment",
            "word_ordinal",
            "start_utf8_byte",
            "candidate",
            "context_key_sha256",
            "adjudication",
            "occurrence_count",
            "field_count",
            "witness_field_key",
        }
        for row in table
    )
    code_row = next(
        row
        for row in table
        if row["candidate"] == "Code actual number of minutes"
    )
    assert code_row["adjudication"] == "whole_domain_denotation"
    assert code_row["word_ordinal"] == 3
    assert code_row["witness_field_key"] == [1976, "V4742"]
    assert not any(
        row["adjudication"] == "unadjudicated_start" for row in table
    )


def test_occurrence_identity_binds_every_start_and_exact_cover() -> None:
    rows = [
        _row(1976, "V4742", COMPILED, RAW_V4742),
        _row(1983, "V9378", COMPILED, RAW_V9378),
    ]
    identity = denotation_candidate_occurrence_identity(rows)
    expected_count = sum(
        denotation_candidate_start_count(row["source_description"])
        for row in rows
    )
    assert identity["row_count"] == expected_count
    assert sum(identity["partition"].values()) == expected_count
    assert identity["partition"]["unadjudicated_start"] == 0
    assert identity["unselected_count"] == 0
    assert identity["overselected_count"] == 0
    assert identity["byte_count"] > 0
    assert len(identity["sha256"]) == 64


def test_frozen_semantic_authorities_have_exact_identity() -> None:
    assert len(TITLE_START_AUTHORITY) == 54_185
    assert len(
        {
            (row[0], row[2], row[3], row[4], row[5])
            for row in TITLE_START_AUTHORITY
        }
    ) == len(TITLE_START_AUTHORITY)
    assert canonical_sha256(TITLE_START_AUTHORITY) == (
        "8be723069f257659cc2c36dd55758c76d084eded24d987629d1950c172032933"
    )
    assert canonical_sha256(TITLE_LITERAL_FAMILIES) == (
        "c5f6b75b64ebd86134e1b655c5d522fcd18dc2179fd28fa2c66a0943465e2913"
    )
    assert len(TITLE_GENERIC_UNIT_FAMILIES) == 38
    assert canonical_sha256(TITLE_GENERIC_UNIT_FAMILIES) == (
        "f709526fe7802085ed691167a595f3d24504523dfa9a5fd4f61eb9269debd9de"
    )

    assert len(PREDICATE_AUTHORITY) == 2_590
    assert len({row[0] for row in PREDICATE_AUTHORITY}) == len(
        PREDICATE_AUTHORITY
    )
    assert canonical_sha256(PREDICATE_AUTHORITY) == (
        "dc4df039cd1c0ae9d31bd8827d07e1bb737c8ee383e6cbe0308789257ba5ff89"
    )

    assert len(CODING_START_AUTHORITY) == 203
    assert len({row[0] for row in CODING_START_AUTHORITY}) == len(
        CODING_START_AUTHORITY
    )
    assert canonical_sha256(CODING_START_AUTHORITY) == (
        "ac2bddbed10bb445215bb19354259685efe24c82b2f59b258dec5d23fcf8497b"
    )
    assert all(
        (selected is not None) == (disposition == "whole_domain_denotation")
        for _candidate, disposition, selected in CODING_START_AUTHORITY
    )

    assert len(SEGMENT_START_AUTHORITY) == 59_445
    assert len({row[0] for row in SEGMENT_START_AUTHORITY}) == len(
        SEGMENT_START_AUTHORITY
    )
    assert sum(
        len(vector) for _segment, vector in SEGMENT_START_AUTHORITY
    ) == (1_114_747)
    assert canonical_sha256(SEGMENT_START_AUTHORITY) == (
        "c0eb8d26bf903137f73afc5fc37e79f8bfd0b2983d9ac79d33f14abd35c84883"
    )
    assert all(
        vector and len(vector) == segment.count(" ") + 1
        for segment, vector in SEGMENT_START_AUTHORITY
    )
    assert all(
        set(vector) <= {"D", "N", "W"}
        for _segment, vector in SEGMENT_START_AUTHORITY
    )
    assert segment_start_authority_table()[0] == {
        "segment": SEGMENT_START_AUTHORITY[0][0],
        "start_dispositions": SEGMENT_START_AUTHORITY[0][1],
        "start_count": len(SEGMENT_START_AUTHORITY[0][1]),
    }


def test_frozen_experience_title_contexts_are_32_selectors_plus_4_body_defeats() -> (
    None
):
    experience_rows = [
        row
        for row in TITLE_START_AUTHORITY
        if re.search(
            r"\bHow many years(?:'| of) experience\b",
            row[1],
            re.IGNORECASE,
        )
    ]
    headers = {row[0]: row[1] for row in experience_rows}
    selector_contexts = {
        context
        for context, header in headers.items()
        if unit_authority._title_selector_spans(header)
    }
    body_defeat_contexts = set(headers) - selector_contexts
    assert len(experience_rows) == 111
    assert len(headers) == 36
    assert len(selector_contexts) == 32
    assert len(body_defeat_contexts) == 4

    selector_rows = [
        row for row in experience_rows if row[0] in selector_contexts
    ]
    positive_by_context = {
        row[0]: row[6]
        for row in selector_rows
        if row[7] == "whole_domain_denotation"
    }
    assert len(positive_by_context) == 32
    assert Counter(positive_by_context.values()) == {
        "year": 11,
        "month": 11,
        "week": 10,
    }
    assert not any(
        row[7] == "whole_domain_denotation"
        for row in experience_rows
        if row[0] in body_defeat_contexts
    )


def test_frozen_typical_week_time_use_has_14_deduplicated_contexts() -> None:
    rows = [
        row
        for row in TITLE_START_AUTHORITY
        if re.match(
            r"^F1(?:[b-h]|d2)\. \(In a typical week, how many hours ",
            row[1],
        )
    ]
    contexts = {row[0] for row in rows}
    positive_contexts = {
        row[0]
        for row in rows
        if row[6] == "hour_per_week"
        and row[7] == "whole_domain_denotation"
        and row[8] == "typical_week_hours_title_denotation"
    }
    assert len(rows) == 78
    assert len(contexts) == 14
    assert positive_contexts == contexts
    assert Counter(
        sum(
            row[7] == "whole_domain_denotation"
            for row in rows
            if row[0] == context
        )
        for context in contexts
    ) == {1: 14}


def test_frozen_highest_college_year_has_46_deduplicated_contexts() -> None:
    rows = [
        row
        for row in TITLE_START_AUTHORITY
        if row[8] == "highest_college_year_title_denotation"
    ]
    assert len(rows) == 46
    assert len({row[0] for row in rows}) == 46
    assert all(
        row[2] == "nominal_year_token"
        and row[6] == "year"
        and row[7] == "whole_domain_denotation"
        for row in rows
    )


def test_frozen_school_years_outside_us_cohort_has_two_year_fields() -> None:
    rows = [
        row
        for row in TITLE_START_AUTHORITY
        if row[8] == "school_years_outside_us_title_denotation"
    ]
    assert {(row[9], row[10]) for row in rows} == {
        (2015, "ER64765"),
        (2015, "ER64904"),
    }
    assert all(
        row[2] == "nominal_year_token"
        and row[6] == "year"
        and row[7] == "whole_domain_denotation"
        for row in rows
    )


def test_frozen_dollars_worth_has_22_deduplicated_contexts() -> None:
    rows = [
        row
        for row in TITLE_START_AUTHORITY
        if "dollars' worth" in row[1].lower()
    ]
    headers = {row[0]: row[1] for row in rows}
    amount_contexts = {
        context
        for context, header in headers.items()
        if "AMOUNT" in header.upper()
        and unit_authority._title_selector_spans(header)
    }
    time_unit_contexts = {
        context
        for context, header in headers.items()
        if "TIME UNIT" in header.upper()
        and unit_authority._title_selector_spans(header)
    }
    nonselector_contexts = set(headers) - amount_contexts - time_unit_contexts
    assert len(rows) == 51
    assert len(headers) == 22
    assert len(amount_contexts) == 10
    assert len(time_unit_contexts) == 10
    assert len(nonselector_contexts) == 2
    assert {
        row[0]
        for row in rows
        if row[6] == "united_states_dollar"
        and row[7] == "whole_domain_denotation"
        and row[8] == "dollars_worth_amount_title_denotation"
    } == amount_contexts
    assert not any(
        row[7] == "whole_domain_denotation"
        for row in rows
        if row[0] in time_unit_contexts
    )
    assert {
        row[0]
        for row in rows
        if row[7] == "whole_domain_denotation"
        and row[0] in nonselector_contexts
    } == nonselector_contexts
    assert Counter(
        (row[2], row[8])
        for row in rows
        if row[8]
        in {
            "delegated_to_primary_statement_grammar",
            "formula_or_operand_defeat",
        }
    ) == {
        (
            "nominal_dollar_token",
            "delegated_to_primary_statement_grammar",
        ): 3,
        (
            "nominal_month_token",
            "formula_or_operand_defeat",
        ): 2,
    }


def test_frozen_number_of_times_has_39_deduplicated_contexts() -> None:
    rows = [
        row
        for row in TITLE_START_AUTHORITY
        if "NUMBER OF TIMES" in normalize_description(row[1]).upper()
    ]
    contexts = {row[0] for row in rows}
    assert len(rows) == 230
    assert len(contexts) == 39
    for context in contexts:
        positive_units = {
            row[6]
            for row in rows
            if row[0] == context and row[7] == "whole_domain_denotation"
        }
        assert positive_units == {"count"}
    assert all(
        row[7] != "whole_domain_denotation"
        for row in rows
        if row[2] == "nominal_minute_token"
    )


def test_frozen_overtime_exception_has_14_amount_and_14_time_unit_fields() -> (
    None
):
    rows = [
        row
        for row in TITLE_START_AUTHORITY
        if re.match(
            r"^(?:BC|DE)14[Bb]4\. How many hours did that overtime amount to\b",
            row[1],
        )
    ]
    amount_fields = {(row[9], row[10]) for row in rows if "--AMOUNT" in row[1]}
    time_unit_fields = {
        (row[9], row[10]) for row in rows if "--TIME UNIT" in row[1]
    }
    assert len(amount_fields) == 14
    assert len(time_unit_fields) == 14
    assert {
        (row[9], row[10])
        for row in rows
        if row[7] == "whole_domain_denotation" and row[6] == "hour"
    } == amount_fields
    assert not any(
        row[7] == "whole_domain_denotation"
        for row in rows
        if (row[9], row[10]) in time_unit_fields
    )


def test_cleartext_start_authorities_replace_the_opaque_hash_registry() -> (
    None
):
    assert not hasattr(
        unit_authority,
        "EXPLICIT_NO_DENOTATION_CANDIDATE_HASHES",
    )


def test_canonical_serialization_matches_section_10_1() -> None:
    assert canonical_json_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}\n'
    assert canonical_sha256([]) == (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    )
