"""Label-verified PSID family income and wealth, waves 2005-2013.

DynaSim scorecard exercise 2 ("Track U", plan
``critical-path-uniform-cut-20260923.md`` work items U4a and U4b) needs,
for every family unit (FU) that holds a cohort member in the year the
member turns 67, the FU's money income by component, its Social Security
and SSI, its reported asset income (which the adjusted income concept
replaces by an annuity) and its wealth excluding home equity (WEALTH1).
This module reads those items from the staged PSID family files.

Scope, verified 2026-09-24 against the staged setup files (``.sps``
labels) and the family codebooks:

========  ============  ===============================  ================
Wave      Income year   Income components (this reader)  WEALTH1
========  ============  ===============================  ================
2005      2004          ER25002-ER28039 (81 items)       not in the file
2007      2006          ER36002-ER41029 (81 items)       not in the file
2009      2008          ER42002-ER46935 (81 items)       ER46968
2011      2010          ER47302-ER52396 (81 items)       ER52392
2013      2012          ER53002-ER58152 (85 items)       ER58209
========  ============  ===============================  ================

**Income.** Every wave carries the PSID-generated family income detail:
head and wife labor income; head (and wife) farm income and the head's
and wife's labor part of unincorporated-business income, which ``LABOR
INCOME OF HEAD``/``OF WIFE`` exclude on the staged files (the taxable
total reconciles only with them added, see :func:`reconcile_family_income`;
the codebook says farm income "includes both labor and asset portions");
head and wife rent, dividends, interest,
trusts/royalties and the asset part of business income; head and wife
transfer components (TANF, SSI, other welfare, pensions and annuities,
unemployment and workers' compensation, child support, alimony, help from
relatives and others, miscellaneous transfers); the OFUM (other FU
members) totals by component; head, wife and OFUM Social Security; the
aggregates; ``TOTAL FAMILY INCOME``; and PSID's ``CENSUS NEEDS STANDARD``
for the income year. The 2011 codebook defines ``TOTAL FAMILY INCOME-2010``
(ER52343) as the sum of seven aggregates: head and wife taxable income
(ER52259), head and wife transfer income (ER52308), OFUM taxable income
(ER52315), OFUM transfer income (ER52336), and head, wife and OFUM Social
Security (ER52337, ER52339, ER52341). The 2013 file splits the wife's
retirement income into pensions, annuities, IRAs and other retirement and
splits the head's ``HEAD ANNUITIES`` into annuities and ``HEAD
IRAS-2012``; earlier files carry one ``WIFE RETIREMENT/ANNUITIES`` item
("Income from Pensions and Annuities"), and their ``HEAD ANNUITIES`` is
"Head's Income from Annuities and IRAs" (2005-2011 codebooks). Head and wife here are the PSID's; "wife"
includes a cohabiting female partner ("Wife"). The accuracy flag of each
Social Security, SSI and asset item is read raw (:data:`ACCURACY_CONCEPTS`;
0 is "Actual value").

**Wealth.** From 2009 the family file carries the imputed wealth
composites (the 2009 documentation: the wealth file "which has been
released in prior waves as a supplement is now part of the 2009 Family
File (ER46936- ER46971)"). The 2005 documentation says "Wealth composite
variables remain in a separate data file within the Data Center"; the
staged 2005 and 2007 setup files carry no label containing ``WEALTH``.
Those supplement files are **not staged** under the PSID data directory,
so :func:`read_family_wealth` refuses waves 2005 and 2007 with
:class:`WealthSupplementNotStagedError`, naming the missing files. The
codebooks define WEALTH1 as the sum of seven asset values net of debts
(2009: one "other debt" item; 2011: five debt types; 2013: farm/business
and real-estate debt split out plus six debt types). The reader keeps the
components so :func:`reconcile_wealth1` can check the identity.

Discipline (as :mod:`populace_dynamics.data.social_security_income` and
:mod:`populace_dynamics.data.family`): each variable is paired with its
exact label in an adjudicated table and verified at read time under
whitespace normalization; no other variable of the wave may carry the
same label; income labels must carry income year ``wave - 1`` and wealth
labels the wave. Amounts are whole dollars; the codebooks state "All
missing data were assigned", so there is no missing sentinel. Negative
values are accepted only where the codebook documents a loss or negative
balance (:data:`MAY_BE_NEGATIVE`); anywhere else a negative amount is
refused. Top codes (for example 9,999,997) are carried as recorded.

What this module does not do: it computes no poverty status, threshold,
annuity or statistic, and it attaches nothing to persons (see
:mod:`populace_dynamics.cohorts.age67`). The reconciliation helpers return
counts of families whose components do not add up; they involve no
threshold.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from populace_dynamics.data import family, psid

__all__ = [
    "ACCURACY_CONCEPTS",
    "ASSET_INCOME_CONCEPTS",
    "FAMILY_INCOME_AGGREGATES",
    "HW_EARNED_CONCEPTS",
    "HW_TRANSFER_COMPONENTS",
    "INCOME_WAVES",
    "MAY_BE_NEGATIVE",
    "OFUM_TRANSFER_COMPONENTS",
    "SOCIAL_SECURITY_CONCEPTS",
    "SSI_CONCEPTS",
    "WEALTH1_DEBTS",
    "WEALTH1_ASSETS",
    "WEALTH_SUPPLEMENT_WAVES",
    "WEALTH_WAVES",
    "WealthSupplementNotAdjudicatedError",
    "WealthSupplementNotStagedError",
    "income_variables",
    "read_family_income",
    "read_family_wealth",
    "reconcile_family_income",
    "reconcile_wealth1",
    "wealth_supplement_status",
    "wealth_variables",
]

#: Waves whose family file this module reads for income (income year is
#: ``wave - 1``).
INCOME_WAVES: tuple[int, ...] = (2005, 2007, 2009, 2011, 2013)
#: Waves whose family file carries the imputed wealth composites.
WEALTH_WAVES: tuple[int, ...] = (2009, 2011, 2013)
#: Waves whose wealth composites sit in a separate PSID supplement file
#: that is not staged (plan section 3, "Wealth staging").
WEALTH_SUPPLEMENT_WAVES: tuple[int, ...] = (2005, 2007)

#: Adjudicated family-file income variables per wave, each with its exact
#: label (verified 2026-09-24 against the staged FAM<wave>ER.sps files).
_INCOME_VARS: dict[int, dict[str, tuple[str, str]]] = {
    2005: {
        "interview": ("ER25002", "2005 FAMILY INTERVIEW (ID) NUMBER"),
        "fu_size": ("ER25016", "# IN FU"),
        "head_age": ("ER25017", "AGE OF HEAD"),
        "head_sex": ("ER25018", "SEX OF HEAD"),
        "wife_age": ("ER25019", "AGE OF WIFE"),
        "n_children": ("ER25020", "# CHILDREN IN FU"),
        "head_labor": ("ER27931", "LABOR INCOME OF HEAD-2004"),
        "head_farm": ("ER27908", "FARM INCOME OF HEAD-2004"),
        "head_business_labor": (
            "ER27910",
            "HD LABOR INCOME FROM BUSINESS-2004",
        ),
        "head_rent": ("ER27932", "HEAD RENT INCOME-2004"),
        "head_dividends": ("ER27934", "HEAD DIVIDENDS-2004"),
        "head_interest": ("ER27936", "HEAD INTEREST INCOME-2004"),
        "head_trusts": ("ER27938", "HEAD INCOME FROM TRUSTS/ROYALTIES-2004"),
        "head_business_asset": (
            "ER27911",
            "HD ASSET INCOME FROM BUSINESS-2004",
        ),
        "wife_labor": ("ER27943", "LABOR INCOME OF WIFE-2004"),
        "wife_business_labor": (
            "ER27940",
            "WF LABOR INCOME FROM BUSINESS-2004",
        ),
        "wife_rent": ("ER27945", "WIFE RENT INCOME-2004"),
        "wife_dividends": ("ER27947", "WIFE DIVIDENDS-2004"),
        "wife_interest": ("ER27949", "WIFE INTEREST INCOME-2004"),
        "wife_trusts": ("ER27951", "WIFE INCOME FROM TRUSTS/ROYALTIES-2004"),
        "wife_business_asset": (
            "ER27941",
            "WF ASSET INCOME FROM BUSINESS-2004",
        ),
        "hw_taxable": ("ER27953", "HEAD AND WIFE TAXABLE INCOME-2004"),
        "head_tanf": ("ER27954", "HEAD INCOME FROM TANF, ETC.-2004"),
        "head_ssi": ("ER27956", "HEAD SSI-2004"),
        "head_other_welfare": ("ER27958", "HEAD OTHER WELFARE-2004"),
        "head_va_pension": ("ER27960", "HEAD VA PENSION-2004"),
        "head_retirement_pensions": (
            "ER27962",
            "HEAD RETIREMENT/PENSIONS-2004",
        ),
        "head_annuities": ("ER27964", "HEAD ANNUITIES-2004"),
        "head_other_retirement": ("ER27966", "HEAD OTHER RETIREMENT-2004"),
        "head_unemployment": (
            "ER27968",
            "HEAD UNEMPLOYMENT COMPENSATION-2004",
        ),
        "head_workers_comp": ("ER27970", "HEAD WORKERS COMPENSATION-2004"),
        "head_child_support": (
            "ER27972",
            "CHILD SUPPORT RECEIVED BY HEAD-2004",
        ),
        "head_alimony": ("ER27974", "HEAD INCOME FROM ALIMONY-2004"),
        "head_help_relatives": ("ER27976", "HEAD HELP FROM RELATIVES-2004"),
        "head_help_others": ("ER27978", "HEAD HELP FROM OTHERS-2004"),
        "head_misc_transfers": (
            "ER27980",
            "HEAD MISCELLANEOUS TRANSFERS-2004",
        ),
        "wife_tanf": ("ER27982", "WIFE INCOME FROM TANF, ETC.-2004"),
        "wife_ssi": ("ER27984", "WIFE SSI-2004"),
        "wife_other_welfare": ("ER27986", "WIFE OTHER WELFARE-2004"),
        "wife_unemployment": (
            "ER27990",
            "WIFE UNEMPLOYMENT COMPENSATION-2004",
        ),
        "wife_workers_comp": ("ER27992", "WIFE WORKERS COMPENSATION-2004"),
        "wife_child_support": (
            "ER27994",
            "CHILD SUPPORT RECEIVED BY WIFE-2004",
        ),
        "wife_help_relatives": ("ER27996", "WIFE HELP FROM RELATIVES-2004"),
        "wife_help_others": ("ER27998", "WIFE HELP FROM OTHERS-2004"),
        "wife_misc_transfers": (
            "ER28000",
            "WIFE MISCELLANEOUS TRANSFERS-2004",
        ),
        "hw_transfer": ("ER28002", "HEAD AND WIFE TRANSFER INCOME-2004"),
        "ofum_labor": ("ER28005", "TOTAL LABOR INCOME OF OTR FU MEMBRS-2004"),
        "ofum_asset": ("ER28007", "TOTAL ASSET INCOME OF OTR FU MEMBRS-2004"),
        "ofum_taxable": ("ER28009", "TAXABLE INCOME OF OTHER FU MEMBERS-2004"),
        "ofum_tanf": ("ER28010", "OTR FU MEMBR INCOME FROM TANF, ETC.-2004"),
        "ofum_ssi": ("ER28012", "OTR FU MEMBERS SSI-2004"),
        "ofum_other_welfare": ("ER28014", "OTR FU MEMBERS OTHER WELFARE-2004"),
        "ofum_va_pension": ("ER28016", "OTHER FU MEMBERS VA PENSION-2004"),
        "ofum_retirement_annuities": (
            "ER28018",
            "OTHER FU MEMBR RETIREMENT/ANNUITIES-2004",
        ),
        "ofum_unemployment": (
            "ER28020",
            "OFUM UNEMPLOYMENT COMPENSATION-2004",
        ),
        "ofum_workers_comp": (
            "ER28022",
            "OTR FU MEMBERS WORKERS COMPENSATION-2004",
        ),
        "ofum_child_support": (
            "ER28024",
            "OFUM INCOME FROM CHILD SUPPORT-2004",
        ),
        "ofum_help_relatives": (
            "ER28026",
            "OTR FU MEMBERS HELP FROM RELATIVES-2004",
        ),
        "ofum_misc_transfers": (
            "ER28028",
            "OFUM MISCELLANEOUS TRANSFERS-2004",
        ),
        "ofum_transfer": ("ER28030", "TOTAL TRANSFER INCOME OF OFUMS-2004"),
        "head_ss": ("ER28031", "HEAD SOCIAL SECURITY INCOME-2004"),
        "wife_ss": ("ER28033", "WIFE SOCIAL SECURITY INCOME-2004"),
        "ofum_ss": ("ER28035", "OFUM SOCIAL SECURITY INCOME-2004"),
        "total_family_income": ("ER28037", "TOTAL FAMILY INCOME-2004"),
        "census_needs_standard": ("ER28039", "CENSUS NEEDS STANDARD-2004"),
        "wife_retirement_annuities": (
            "ER27988",
            "WIFE RETIREMENT/ANNUITIES-2004",
        ),
    },
    2007: {
        "interview": ("ER36002", "2007 FAMILY INTERVIEW (ID) NUMBER"),
        "fu_size": ("ER36016", "# IN FU"),
        "head_age": ("ER36017", "AGE OF HEAD"),
        "head_sex": ("ER36018", "SEX OF HEAD"),
        "wife_age": ("ER36019", "AGE OF WIFE"),
        "n_children": ("ER36020", "# CHILDREN IN FU"),
        "head_labor": ("ER40921", "LABOR INCOME OF HEAD-2006"),
        "head_farm": ("ER40898", "FARM INCOME OF HEAD-2006"),
        "head_business_labor": (
            "ER40900",
            "HD LABOR INCOME FROM BUSINESS-2006",
        ),
        "head_rent": ("ER40922", "HEAD RENT INCOME-2006"),
        "head_dividends": ("ER40924", "HEAD DIVIDENDS-2006"),
        "head_interest": ("ER40926", "HEAD INTEREST INCOME-2006"),
        "head_trusts": ("ER40928", "HEAD INCOME FROM TRUSTS/ROYALTIES-2006"),
        "head_business_asset": (
            "ER40901",
            "HD ASSET INCOME FROM BUSINESS-2006",
        ),
        "wife_labor": ("ER40933", "LABOR INCOME OF WIFE-2006"),
        "wife_business_labor": (
            "ER40930",
            "WF LABOR INCOME FROM BUSINESS-2006",
        ),
        "wife_rent": ("ER40935", "WIFE RENT INCOME-2006"),
        "wife_dividends": ("ER40937", "WIFE DIVIDENDS-2006"),
        "wife_interest": ("ER40939", "WIFE INTEREST INCOME-2006"),
        "wife_trusts": ("ER40941", "WIFE INCOME FROM TRUSTS/ROYALTIES-2006"),
        "wife_business_asset": (
            "ER40931",
            "WF ASSET INCOME FROM BUSINESS-2006",
        ),
        "hw_taxable": ("ER40943", "HEAD AND WIFE TAXABLE INCOME-2006"),
        "head_tanf": ("ER40944", "HEAD INCOME FROM TANF, ETC.-2006"),
        "head_ssi": ("ER40946", "HEAD SSI-2006"),
        "head_other_welfare": ("ER40948", "HEAD OTHER WELFARE-2006"),
        "head_va_pension": ("ER40950", "HEAD VA PENSION-2006"),
        "head_retirement_pensions": (
            "ER40952",
            "HEAD RETIREMENT/PENSIONS-2006",
        ),
        "head_annuities": ("ER40954", "HEAD ANNUITIES-2006"),
        "head_other_retirement": ("ER40956", "HEAD OTHER RETIREMENT-2006"),
        "head_unemployment": (
            "ER40958",
            "HEAD UNEMPLOYMENT COMPENSATION-2006",
        ),
        "head_workers_comp": ("ER40960", "HEAD WORKERS COMPENSATION-2006"),
        "head_child_support": (
            "ER40962",
            "CHILD SUPPORT RECEIVED BY HEAD-2006",
        ),
        "head_alimony": ("ER40964", "HEAD INCOME FROM ALIMONY-2006"),
        "head_help_relatives": ("ER40966", "HEAD HELP FROM RELATIVES-2006"),
        "head_help_others": ("ER40968", "HEAD HELP FROM OTHERS-2006"),
        "head_misc_transfers": (
            "ER40970",
            "HEAD MISCELLANEOUS TRANSFERS-2006",
        ),
        "wife_tanf": ("ER40972", "WIFE INCOME FROM TANF, ETC.-2006"),
        "wife_ssi": ("ER40974", "WIFE SSI-2006"),
        "wife_other_welfare": ("ER40976", "WIFE OTHER WELFARE-2006"),
        "wife_unemployment": (
            "ER40980",
            "WIFE UNEMPLOYMENT COMPENSATION-2006",
        ),
        "wife_workers_comp": ("ER40982", "WIFE WORKERS COMPENSATION-2006"),
        "wife_child_support": (
            "ER40984",
            "CHILD SUPPORT RECEIVED BY WIFE-2006",
        ),
        "wife_help_relatives": ("ER40986", "WIFE HELP FROM RELATIVES-2006"),
        "wife_help_others": ("ER40988", "WIFE HELP FROM OTHERS-2006"),
        "wife_misc_transfers": (
            "ER40990",
            "WIFE MISCELLANEOUS TRANSFERS-2006",
        ),
        "hw_transfer": ("ER40992", "HEAD AND WIFE TRANSFER INCOME-2006"),
        "ofum_labor": ("ER40995", "TOTAL LABOR INCOME OF OTR FU MEMBRS-2006"),
        "ofum_asset": ("ER40997", "TOTAL ASSET INCOME OF OTR FU MEMBRS-2006"),
        "ofum_taxable": ("ER40999", "TAXABLE INCOME OF OTHER FU MEMBERS-2006"),
        "ofum_tanf": ("ER41000", "OTR FU MEMBR INCOME FROM TANF, ETC.-2006"),
        "ofum_ssi": ("ER41002", "OTR FU MEMBERS SSI-2006"),
        "ofum_other_welfare": ("ER41004", "OTR FU MEMBERS OTHER WELFARE-2006"),
        "ofum_va_pension": ("ER41006", "OTHER FU MEMBERS VA PENSION-2006"),
        "ofum_retirement_annuities": (
            "ER41008",
            "OTHER FU MEMBR RETIREMENT/ANNUITIES-2006",
        ),
        "ofum_unemployment": (
            "ER41010",
            "OFUM UNEMPLOYMENT COMPENSATION-2006",
        ),
        "ofum_workers_comp": (
            "ER41012",
            "OTR FU MEMBERS WORKERS COMPENSATION-2006",
        ),
        "ofum_child_support": (
            "ER41014",
            "OFUM INCOME FROM CHILD SUPPORT-2006",
        ),
        "ofum_help_relatives": (
            "ER41016",
            "OTR FU MEMBERS HELP FROM RELATIVES-2006",
        ),
        "ofum_misc_transfers": (
            "ER41018",
            "OFUM MISCELLANEOUS TRANSFERS-2006",
        ),
        "ofum_transfer": ("ER41020", "TOTAL TRANSFER INCOME OF OFUMS-2006"),
        "head_ss": ("ER41021", "HEAD SOCIAL SECURITY INCOME-2006"),
        "wife_ss": ("ER41023", "WIFE SOCIAL SECURITY INCOME-2006"),
        "ofum_ss": ("ER41025", "OFUM SOCIAL SECURITY INCOME-2006"),
        "total_family_income": ("ER41027", "TOTAL FAMILY INCOME-2006"),
        "census_needs_standard": ("ER41029", "CENSUS NEEDS STANDARD-2006"),
        "wife_retirement_annuities": (
            "ER40978",
            "WIFE RETIREMENT/ANNUITIES-2006",
        ),
    },
    2009: {
        "interview": ("ER42002", "2009 FAMILY INTERVIEW (ID) NUMBER"),
        "fu_size": ("ER42016", "# IN FU"),
        "head_age": ("ER42017", "AGE OF HEAD"),
        "head_sex": ("ER42018", "SEX OF HEAD"),
        "wife_age": ("ER42019", "AGE OF WIFE"),
        "n_children": ("ER42020", "# CHILDREN IN FU"),
        "head_labor": ("ER46829", "LABOR INCOME OF HEAD-2008"),
        "head_farm": ("ER46806", "FARM INCOME OF HEAD-2008"),
        "head_business_labor": (
            "ER46808",
            "HD LABOR INCOME FROM BUSINESS-2008",
        ),
        "head_rent": ("ER46830", "HEAD RENT INCOME-2008"),
        "head_dividends": ("ER46832", "HEAD DIVIDENDS-2008"),
        "head_interest": ("ER46834", "HEAD INTEREST INCOME-2008"),
        "head_trusts": ("ER46836", "HEAD INCOME FROM TRUSTS/ROYALTIES-2008"),
        "head_business_asset": (
            "ER46809",
            "HD ASSET INCOME FROM BUSINESS-2008",
        ),
        "wife_labor": ("ER46841", "LABOR INCOME OF WIFE-2008"),
        "wife_business_labor": (
            "ER46838",
            "WF LABOR INCOME FROM BUSINESS-2008",
        ),
        "wife_rent": ("ER46843", "WIFE RENT INCOME-2008"),
        "wife_dividends": ("ER46845", "WIFE DIVIDENDS-2008"),
        "wife_interest": ("ER46847", "WIFE INTEREST INCOME-2008"),
        "wife_trusts": ("ER46849", "WIFE INCOME FROM TRUSTS/ROYALTIES-2008"),
        "wife_business_asset": (
            "ER46839",
            "WF ASSET INCOME FROM BUSINESS-2008",
        ),
        "hw_taxable": ("ER46851", "HEAD AND WIFE TAXABLE INCOME-2008"),
        "head_tanf": ("ER46852", "HEAD INCOME FROM TANF, ETC.-2008"),
        "head_ssi": ("ER46854", "HEAD SSI-2008"),
        "head_other_welfare": ("ER46856", "HEAD OTHER WELFARE-2008"),
        "head_va_pension": ("ER46858", "HEAD VA PENSION-2008"),
        "head_retirement_pensions": (
            "ER46860",
            "HEAD RETIREMENT/PENSIONS-2008",
        ),
        "head_annuities": ("ER46862", "HEAD ANNUITIES-2008"),
        "head_other_retirement": ("ER46864", "HEAD OTHER RETIREMENT-2008"),
        "head_unemployment": (
            "ER46866",
            "HEAD UNEMPLOYMENT COMPENSATION-2008",
        ),
        "head_workers_comp": ("ER46868", "HEAD WORKERS COMPENSATION-2008"),
        "head_child_support": (
            "ER46870",
            "CHILD SUPPORT RECEIVED BY HEAD-2008",
        ),
        "head_alimony": ("ER46872", "HEAD INCOME FROM ALIMONY-2008"),
        "head_help_relatives": ("ER46874", "HEAD HELP FROM RELATIVES-2008"),
        "head_help_others": ("ER46876", "HEAD HELP FROM OTHERS-2008"),
        "head_misc_transfers": (
            "ER46878",
            "HEAD MISCELLANEOUS TRANSFERS-2008",
        ),
        "wife_tanf": ("ER46880", "WIFE INCOME FROM TANF, ETC.-2008"),
        "wife_ssi": ("ER46882", "WIFE SSI-2008"),
        "wife_other_welfare": ("ER46884", "WIFE OTHER WELFARE-2008"),
        "wife_unemployment": (
            "ER46888",
            "WIFE UNEMPLOYMENT COMPENSATION-2008",
        ),
        "wife_workers_comp": ("ER46890", "WIFE WORKERS COMPENSATION-2008"),
        "wife_child_support": (
            "ER46892",
            "CHILD SUPPORT RECEIVED BY WIFE-2008",
        ),
        "wife_help_relatives": ("ER46894", "WIFE HELP FROM RELATIVES-2008"),
        "wife_help_others": ("ER46896", "WIFE HELP FROM OTHERS-2008"),
        "wife_misc_transfers": (
            "ER46898",
            "WIFE MISCELLANEOUS TRANSFERS-2008",
        ),
        "hw_transfer": ("ER46900", "HEAD AND WIFE TRANSFER INCOME-2008"),
        "ofum_labor": ("ER46903", "TOTAL LABOR INCOME OF OTR FU MEMBRS-2008"),
        "ofum_asset": ("ER46905", "TOTAL ASSET INCOME OF OTR FU MEMBRS-2008"),
        "ofum_taxable": ("ER46907", "TAXABLE INCOME OF OTHER FU MEMBERS-2008"),
        "ofum_tanf": ("ER46908", "OTR FU MEMBR INCOME FROM TANF, ETC.-2008"),
        "ofum_ssi": ("ER46910", "OTR FU MEMBERS SSI-2008"),
        "ofum_other_welfare": ("ER46912", "OTR FU MEMBERS OTHER WELFARE-2008"),
        "ofum_va_pension": ("ER46914", "OTHER FU MEMBERS VA PENSION-2008"),
        "ofum_retirement_annuities": (
            "ER46916",
            "OTHER FU MEMBR RETIREMENT/ANNUITIES-2008",
        ),
        "ofum_unemployment": (
            "ER46918",
            "OFUM UNEMPLOYMENT COMPENSATION-2008",
        ),
        "ofum_workers_comp": (
            "ER46920",
            "OTR FU MEMBERS WORKERS COMPENSATION-2008",
        ),
        "ofum_child_support": (
            "ER46922",
            "OFUM INCOME FROM CHILD SUPPORT-2008",
        ),
        "ofum_help_relatives": (
            "ER46924",
            "OTR FU MEMBERS HELP FROM RELATIVES-2008",
        ),
        "ofum_misc_transfers": (
            "ER46926",
            "OFUM MISCELLANEOUS TRANSFERS-2008",
        ),
        "ofum_transfer": ("ER46928", "TOTAL TRANSFER INCOME OF OFUMS-2008"),
        "head_ss": ("ER46929", "HEAD SOCIAL SECURITY INCOME-2008"),
        "wife_ss": ("ER46931", "WIFE SOCIAL SECURITY INCOME-2008"),
        "ofum_ss": ("ER46933", "OFUM SOCIAL SECURITY INCOME-2008"),
        "total_family_income": ("ER46935", "TOTAL FAMILY INCOME-2008"),
        "census_needs_standard": ("ER46972", "CENSUS NEEDS STANDARD-2008"),
        "wife_retirement_annuities": (
            "ER46886",
            "WIFE RETIREMENT/ANNUITIES-2008",
        ),
    },
    2011: {
        "interview": ("ER47302", "2011 FAMILY INTERVIEW (ID) NUMBER"),
        "fu_size": ("ER47316", "# IN FU"),
        "head_age": ("ER47317", "AGE OF HEAD"),
        "head_sex": ("ER47318", "SEX OF HEAD"),
        "wife_age": ("ER47319", "AGE OF WIFE"),
        "n_children": ("ER47320", "# CHILDREN IN FU"),
        "head_labor": ("ER52237", "LABOR INCOME OF HEAD-2010"),
        "head_farm": ("ER52214", "FARM INCOME OF HEAD-2010"),
        "head_business_labor": (
            "ER52216",
            "HD LABOR INCOME FROM BUSINESS-2010",
        ),
        "head_rent": ("ER52238", "HEAD RENT INCOME-2010"),
        "head_dividends": ("ER52240", "HEAD DIVIDENDS-2010"),
        "head_interest": ("ER52242", "HEAD INTEREST INCOME-2010"),
        "head_trusts": ("ER52244", "HEAD INCOME FROM TRUSTS/ROYALTIES-2010"),
        "head_business_asset": (
            "ER52217",
            "HD ASSET INCOME FROM BUSINESS-2010",
        ),
        "wife_labor": ("ER52249", "LABOR INCOME OF WIFE-2010"),
        "wife_business_labor": (
            "ER52246",
            "WF LABOR INCOME FROM BUSINESS-2010",
        ),
        "wife_rent": ("ER52251", "WIFE RENT INCOME-2010"),
        "wife_dividends": ("ER52253", "WIFE DIVIDENDS-2010"),
        "wife_interest": ("ER52255", "WIFE INTEREST INCOME-2010"),
        "wife_trusts": ("ER52257", "WIFE INCOME FROM TRUSTS/ROYALTIES-2010"),
        "wife_business_asset": (
            "ER52247",
            "WF ASSET INCOME FROM BUSINESS-2010",
        ),
        "hw_taxable": ("ER52259", "HEAD AND WIFE TAXABLE INCOME-2010"),
        "head_tanf": ("ER52260", "HEAD INCOME FROM TANF, ETC.-2010"),
        "head_ssi": ("ER52262", "HEAD SSI-2010"),
        "head_other_welfare": ("ER52264", "HEAD OTHER WELFARE-2010"),
        "head_va_pension": ("ER52266", "HEAD VA PENSION-2010"),
        "head_retirement_pensions": (
            "ER52268",
            "HEAD RETIREMENT/PENSIONS-2010",
        ),
        "head_annuities": ("ER52270", "HEAD ANNUITIES-2010"),
        "head_other_retirement": ("ER52272", "HEAD OTHER RETIREMENT-2010"),
        "head_unemployment": (
            "ER52274",
            "HEAD UNEMPLOYMENT COMPENSATION-2010",
        ),
        "head_workers_comp": ("ER52276", "HEAD WORKERS COMPENSATION-2010"),
        "head_child_support": (
            "ER52278",
            "CHILD SUPPORT RECEIVED BY HEAD-2010",
        ),
        "head_alimony": ("ER52280", "HEAD INCOME FROM ALIMONY-2010"),
        "head_help_relatives": ("ER52282", "HEAD HELP FROM RELATIVES-2010"),
        "head_help_others": ("ER52284", "HEAD HELP FROM OTHERS-2010"),
        "head_misc_transfers": (
            "ER52286",
            "HEAD MISCELLANEOUS TRANSFERS-2010",
        ),
        "wife_tanf": ("ER52288", "WIFE INCOME FROM TANF, ETC.-2010"),
        "wife_ssi": ("ER52290", "WIFE SSI-2010"),
        "wife_other_welfare": ("ER52292", "WIFE OTHER WELFARE-2010"),
        "wife_unemployment": (
            "ER52296",
            "WIFE UNEMPLOYMENT COMPENSATION-2010",
        ),
        "wife_workers_comp": ("ER52298", "WIFE WORKERS COMPENSATION-2010"),
        "wife_child_support": (
            "ER52300",
            "CHILD SUPPORT RECEIVED BY WIFE-2010",
        ),
        "wife_help_relatives": ("ER52302", "WIFE HELP FROM RELATIVES-2010"),
        "wife_help_others": ("ER52304", "WIFE HELP FROM OTHERS-2010"),
        "wife_misc_transfers": (
            "ER52306",
            "WIFE MISCELLANEOUS TRANSFERS-2010",
        ),
        "hw_transfer": ("ER52308", "HEAD AND WIFE TRANSFER INCOME-2010"),
        "ofum_labor": ("ER52311", "TOTAL LABOR INCOME OF OTR FU MEMBRS-2010"),
        "ofum_asset": ("ER52313", "TOTAL ASSET INCOME OF OTR FU MEMBRS-2010"),
        "ofum_taxable": ("ER52315", "TAXABLE INCOME OF OTHER FU MEMBERS-2010"),
        "ofum_tanf": ("ER52316", "OTR FU MEMBR INCOME FROM TANF, ETC.-2010"),
        "ofum_ssi": ("ER52318", "OTR FU MEMBERS SSI-2010"),
        "ofum_other_welfare": ("ER52320", "OTR FU MEMBERS OTHER WELFARE-2010"),
        "ofum_va_pension": ("ER52322", "OTHER FU MEMBERS VA PENSION-2010"),
        "ofum_retirement_annuities": (
            "ER52324",
            "OTHER FU MEMBR RETIREMENT/ANNUITIES-2010",
        ),
        "ofum_unemployment": (
            "ER52326",
            "OFUM UNEMPLOYMENT COMPENSATION-2010",
        ),
        "ofum_workers_comp": (
            "ER52328",
            "OTR FU MEMBERS WORKERS COMPENSATION-2010",
        ),
        "ofum_child_support": (
            "ER52330",
            "OFUM INCOME FROM CHILD SUPPORT-2010",
        ),
        "ofum_help_relatives": (
            "ER52332",
            "OTR FU MEMBERS HELP FROM RELATIVES-2010",
        ),
        "ofum_misc_transfers": (
            "ER52334",
            "OFUM MISCELLANEOUS TRANSFERS-2010",
        ),
        "ofum_transfer": ("ER52336", "TOTAL TRANSFER INCOME OF OFUMS-2010"),
        "head_ss": ("ER52337", "HEAD SOCIAL SECURITY INCOME-2010"),
        "wife_ss": ("ER52339", "WIFE SOCIAL SECURITY INCOME-2010"),
        "ofum_ss": ("ER52341", "OFUM SOCIAL SECURITY INCOME-2010"),
        "total_family_income": ("ER52343", "TOTAL FAMILY INCOME-2010"),
        "census_needs_standard": ("ER52396", "CENSUS NEEDS STANDARD-2010"),
        "wife_retirement_annuities": (
            "ER52294",
            "WIFE RETIREMENT/ANNUITIES-2010",
        ),
    },
    2013: {
        "interview": ("ER53002", "2013 FAMILY INTERVIEW (ID) NUMBER"),
        "fu_size": ("ER53016", "# IN FU"),
        "head_age": ("ER53017", "AGE OF HEAD"),
        "head_sex": ("ER53018", "SEX OF HEAD"),
        "wife_age": ("ER53019", "AGE OF WIFE"),
        "n_children": ("ER53020", "# CHILDREN IN FU"),
        "head_labor": ("ER58038", "LABOR INCOME OF HEAD-2012"),
        "head_farm": ("ER58015", "FARM INCOME OF HEAD-2012"),
        "head_business_labor": (
            "ER58017",
            "HD LABOR INCOME FROM BUSINESS-2012",
        ),
        "head_rent": ("ER58039", "HEAD RENT INCOME-2012"),
        "head_dividends": ("ER58041", "HEAD DIVIDENDS-2012"),
        "head_interest": ("ER58043", "HEAD INTEREST INCOME-2012"),
        "head_trusts": ("ER58045", "HEAD INCOME FROM TRUSTS/ROYALTIES-2012"),
        "head_business_asset": (
            "ER58018",
            "HD ASSET INCOME FROM BUSINESS-2012",
        ),
        "wife_labor": ("ER58050", "LABOR INCOME OF WIFE-2012"),
        "wife_business_labor": (
            "ER58047",
            "WF LABOR INCOME FROM BUSINESS-2012",
        ),
        "wife_rent": ("ER58052", "WIFE RENT INCOME-2012"),
        "wife_dividends": ("ER58054", "WIFE DIVIDENDS-2012"),
        "wife_interest": ("ER58056", "WIFE INTEREST INCOME-2012"),
        "wife_trusts": ("ER58058", "WIFE INCOME FROM TRUSTS/ROYALTIES-2012"),
        "wife_business_asset": (
            "ER58048",
            "WF ASSET INCOME FROM BUSINESS-2012",
        ),
        "hw_taxable": ("ER58060", "HEAD AND WIFE TAXABLE INCOME-2012"),
        "head_tanf": ("ER58061", "HEAD INCOME FROM TANF, ETC.-2012"),
        "head_ssi": ("ER58063", "HEAD SSI-2012"),
        "head_other_welfare": ("ER58065", "HEAD OTHER WELFARE-2012"),
        "head_va_pension": ("ER58067", "HEAD VA PENSION-2012"),
        "head_retirement_pensions": (
            "ER58069",
            "HEAD RETIREMENT/PENSIONS-2012",
        ),
        "head_annuities": ("ER58071", "HEAD ANNUITIES-2012"),
        "head_other_retirement": ("ER58075", "HEAD OTHER RETIREMENT-2012"),
        "head_unemployment": (
            "ER58077",
            "HEAD UNEMPLOYMENT COMPENSATION-2012",
        ),
        "head_workers_comp": ("ER58079", "HEAD WORKERS COMPENSATION-2012"),
        "head_child_support": (
            "ER58081",
            "CHILD SUPPORT RECEIVED BY HEAD-2012",
        ),
        "head_alimony": ("ER58083", "HEAD INCOME FROM ALIMONY-2012"),
        "head_help_relatives": ("ER58085", "HEAD HELP FROM RELATIVES-2012"),
        "head_help_others": ("ER58087", "HEAD HELP FROM OTHERS-2012"),
        "head_misc_transfers": (
            "ER58089",
            "HEAD MISCELLANEOUS TRANSFERS-2012",
        ),
        "wife_tanf": ("ER58091", "WIFE INCOME FROM TANF, ETC.-2012"),
        "wife_ssi": ("ER58093", "WIFE SSI-2012"),
        "wife_other_welfare": ("ER58095", "WIFE OTHER WELFARE-2012"),
        "wife_unemployment": (
            "ER58105",
            "WIFE UNEMPLOYMENT COMPENSATION-2012",
        ),
        "wife_workers_comp": ("ER58107", "WIFE WORKERS COMPENSATION-2012"),
        "wife_child_support": (
            "ER58109",
            "CHILD SUPPORT RECEIVED BY WIFE-2012",
        ),
        "wife_help_relatives": ("ER58111", "WIFE HELP FROM RELATIVES-2012"),
        "wife_help_others": ("ER58113", "WIFE HELP FROM OTHERS-2012"),
        "wife_misc_transfers": (
            "ER58115",
            "WIFE MISCELLANEOUS TRANSFERS-2012",
        ),
        "hw_transfer": ("ER58117", "HEAD AND WIFE TRANSFER INCOME-2012"),
        "ofum_labor": ("ER58120", "TOTAL LABOR INCOME OF OTR FU MEMBRS-2012"),
        "ofum_asset": ("ER58122", "TOTAL ASSET INCOME OF OTR FU MEMBRS-2012"),
        "ofum_taxable": ("ER58124", "TAXABLE INCOME OF OTHER FU MEMBERS-2012"),
        "ofum_tanf": ("ER58125", "OTR FU MEMBR INCOME FROM TANF, ETC.-2012"),
        "ofum_ssi": ("ER58127", "OTR FU MEMBERS SSI-2012"),
        "ofum_other_welfare": ("ER58129", "OTR FU MEMBERS OTHER WELFARE-2012"),
        "ofum_va_pension": ("ER58131", "OTHER FU MEMBERS VA PENSION-2012"),
        "ofum_retirement_annuities": (
            "ER58133",
            "OTHER FU MEMBR RETIREMENT/ANNUITIES-2012",
        ),
        "ofum_unemployment": (
            "ER58135",
            "OFUM UNEMPLOYMENT COMPENSATION-2012",
        ),
        "ofum_workers_comp": (
            "ER58137",
            "OTR FU MEMBERS WORKERS COMPENSATION-2012",
        ),
        "ofum_child_support": (
            "ER58139",
            "OFUM INCOME FROM CHILD SUPPORT-2012",
        ),
        "ofum_help_relatives": (
            "ER58141",
            "OTR FU MEMBERS HELP FROM RELATIVES-2012",
        ),
        "ofum_misc_transfers": (
            "ER58143",
            "OFUM MISCELLANEOUS TRANSFERS-2012",
        ),
        "ofum_transfer": ("ER58145", "TOTAL TRANSFER INCOME OF OFUMS-2012"),
        "head_ss": ("ER58146", "HEAD SOCIAL SECURITY INCOME-2012"),
        "wife_ss": ("ER58148", "WIFE SOCIAL SECURITY INCOME-2012"),
        "ofum_ss": ("ER58150", "OFUM SOCIAL SECURITY INCOME-2012"),
        "total_family_income": ("ER58152", "TOTAL FAMILY INCOME-2012"),
        "census_needs_standard": ("ER58213", "CENSUS NEEDS STANDARD-2012"),
        "head_iras": ("ER58073", "HEAD IRAS-2012"),
        "wife_retirement_pensions": (
            "ER58097",
            "WIFE RETIREMENT/PENSIONS-2012",
        ),
        "wife_annuities": ("ER58099", "WIFE ANNUITIES-2012"),
        "wife_iras": ("ER58101", "WIFE IRAS-2012"),
        "wife_other_retirement": ("ER58103", "WIFE OTHER RETIREMENT-2012"),
    },
}

#: Adjudicated family-file wealth variables per wave (2009-2013 only).
_WEALTH_VARS: dict[int, dict[str, tuple[str, str]]] = {
    2009: {
        "wealth1": ("ER46968", "IMP WEALTH W/O EQUITY (WEALTH1) 09"),
        "wealth1_acc": ("ER46969", "ACC WEALTH W/O EQUITY (WEALTH1) 09"),
        "wealth2": ("ER46970", "IMP WEALTH W/ EQUITY (WEALTH2) 09"),
        "home_equity": ("ER46966", "IMP VALUE HOME EQUITY 09"),
        "vehicles": ("ER46956", "IMP VALUE VEHICLES (W6) 09"),
        "checking_saving": ("ER46942", "IMP VAL CHECKING/SAVING (W28) 09"),
        "stocks": ("ER46954", "IMP VALUE STOCKS (W16) 09"),
        "other_assets": ("ER46960", "IMP VALUE OTH ASSETS (W34) 09"),
        "ira_annuity": ("ER46964", "IMP VALUE ANNUITY/IRA (W22) 09"),
        "farm_business": ("ER46938", "IMP VALUE FARM/BUS (W11) 09"),
        "other_real_estate": ("ER46950", "IMP VAL OTH REAL ESTATE (W2) 09"),
        "other_debt": ("ER46946", "IMP VALUE OTH DEBT (W39) 09"),
    },
    2011: {
        "wealth1": ("ER52392", "IMP WEALTH W/O EQUITY (WEALTH1) 11"),
        "wealth1_acc": ("ER52393", "ACC WEALTH W/O EQUITY (WEALTH1) 11"),
        "wealth2": ("ER52394", "IMP WEALTH W/ EQUITY (WEALTH2) 11"),
        "home_equity": ("ER52390", "IMP VALUE HOME EQUITY 11"),
        "vehicles": ("ER52360", "IMP VALUE VEHICLES (W6) 11"),
        "checking_saving": ("ER52350", "IMP VAL CHECKING/SAVING (W28) 11"),
        "stocks": ("ER52358", "IMP VALUE STOCKS (W16) 11"),
        "other_assets": ("ER52364", "IMP VALUE OTH ASSETS (W34) 11"),
        "ira_annuity": ("ER52368", "IMP VALUE ANNUITY/IRA (W22) 11"),
        "farm_business": ("ER52346", "IMP VALUE FARM/BUS (W11) 11"),
        "other_real_estate": ("ER52354", "IMP VAL OTH REAL ESTATE (W2) 11"),
        "credit_card_debt": ("ER52372", "IMP VAL CREDIT CARD DEBT (W39A) 11"),
        "student_loan_debt": (
            "ER52376",
            "IMP VAL STUDENT LOAN DEBT (W39B1) 11",
        ),
        "medical_debt": ("ER52380", "IMP VAL MEDICAL DEBT (W39B2) 11"),
        "legal_debt": ("ER52384", "IMP VAL LEGAL DEBT (W39B3) 11"),
        "family_loan_debt": ("ER52388", "IMP VAL FAMILY LOAN DEBT (W39B4) 11"),
    },
    2013: {
        "wealth1": ("ER58209", "IMP WEALTH W/O EQUITY (WEALTH1) 2013"),
        "wealth1_acc": ("ER58210", "ACC WEALTH W/O EQUITY (WEALTH1) 2013"),
        "wealth2": ("ER58211", "IMP WEALTH W/ EQUITY (WEALTH2) 2013"),
        "home_equity": ("ER58207", "IMP VALUE HOME EQUITY 2013"),
        "vehicles": ("ER58173", "IMP VALUE VEHICLES (W6) 2013"),
        "checking_saving": ("ER58161", "IMP VAL CHECKING/SAVING (W28) 2013"),
        "stocks": ("ER58171", "IMP VALUE STOCKS (W16) 2013"),
        "other_assets": ("ER58177", "IMP VALUE OTH ASSETS (W34) 2013"),
        "ira_annuity": ("ER58181", "IMP VALUE ANNUITY/IRA (W22) 2013"),
        "credit_card_debt": (
            "ER58185",
            "IMP VAL CREDIT CARD DEBT (W39A) 2013",
        ),
        "student_loan_debt": (
            "ER58189",
            "IMP VAL STUDENT LOAN DEBT (W39B1) 2013",
        ),
        "medical_debt": ("ER58193", "IMP VAL MEDICAL DEBT (W39B2) 2013"),
        "legal_debt": ("ER58197", "IMP VAL LEGAL DEBT (W39B3) 2013"),
        "family_loan_debt": (
            "ER58201",
            "IMP VAL FAMILY LOAN DEBT (W39B4) 2013",
        ),
        "farm_business_asset": (
            "ER58155",
            "IMP VALUE FARM/BUS ASSET (W11A) 2013",
        ),
        "farm_business_debt": (
            "ER58157",
            "IMP VALUE FARM/BUS DEBT (W11B) 2013",
        ),
        "other_real_estate_asset": (
            "ER58165",
            "IMP VAL OTH REAL ESTATE ASSET (W2A) 2013",
        ),
        "other_real_estate_debt": (
            "ER58167",
            "IMP VAL OTH REAL ESTATE DEBT (W2B) 2013",
        ),
        "other_debt": ("ER58205", "IMP VAL OTHER DEBT (W38B7) 2013"),
    },
}

#: Adjudicated accuracy flags of the Social Security, SSI and asset items
#: (the variable after each amount in the layout; labels verified
#: 2026-09-24).  Codes are carried raw: 0 is "Actual value" in the
#: codebooks read; the other codes mark imputations of different kinds
#: (the OFUM asset item documents 2-6, the head and wife items 1 and 5).
_ACCURACY_VARS: dict[int, dict[str, tuple[str, str]]] = {
    2005: {
        "head_ss_acc": ("ER28032", "ACCURACY OF HEAD SOCIAL SECURITY-2004"),
        "wife_ss_acc": ("ER28034", "ACCURACY OF WIFE SOCIAL SECURITY-2004"),
        "ofum_ss_acc": ("ER28036", "ACCURACY OF OFUM SOCIAL SECURITY-2004"),
        "head_ssi_acc": ("ER27957", "ACCURACY OF HEAD SSI-2004"),
        "wife_ssi_acc": ("ER27985", "ACCURACY OF WIFE SSI-2004"),
        "ofum_ssi_acc": ("ER28013", "ACCURACY OF OTR FU MEMBERS SSI-2004"),
        "head_rent_acc": ("ER27933", "ACCURACY OF HEAD RENT INCOME-2004"),
        "head_dividends_acc": ("ER27935", "ACCURACY OF HEAD DIVIDENDS-2004"),
        "head_interest_acc": (
            "ER27937",
            "ACCURACY OF HEAD INTEREST INCOME-2004",
        ),
        "head_trusts_acc": (
            "ER27939",
            "ACCURACY OF HD INCOME FROM TRUSTS-2004",
        ),
        "wife_rent_acc": ("ER27946", "ACCURACY OF WIFE RENT INCOME-2004"),
        "wife_dividends_acc": ("ER27948", "ACCURACY OF WIFE DIVIDENDS-2004"),
        "wife_interest_acc": (
            "ER27950",
            "ACCURACY OF WIFE INTEREST INCOME-2004",
        ),
        "wife_trusts_acc": (
            "ER27952",
            "ACCURACY OF WF INCOME FROM TRUSTS-2004",
        ),
        "ofum_asset_acc": ("ER28008", "ACCURACY OF OTR FU MEMBR ASSET Y-2004"),
    },
    2007: {
        "head_ss_acc": ("ER41022", "ACCURACY OF HEAD SOCIAL SECURITY-2006"),
        "wife_ss_acc": ("ER41024", "ACCURACY OF WIFE SOCIAL SECURITY-2006"),
        "ofum_ss_acc": ("ER41026", "ACCURACY OF OFUM SOCIAL SECURITY-2006"),
        "head_ssi_acc": ("ER40947", "ACCURACY OF HEAD SSI-2006"),
        "wife_ssi_acc": ("ER40975", "ACCURACY OF WIFE SSI-2006"),
        "ofum_ssi_acc": ("ER41003", "ACCURACY OF OTR FU MEMBERS SSI-2006"),
        "head_rent_acc": ("ER40923", "ACCURACY OF HEAD RENT INCOME-2006"),
        "head_dividends_acc": ("ER40925", "ACCURACY OF HEAD DIVIDENDS-2006"),
        "head_interest_acc": (
            "ER40927",
            "ACCURACY OF HEAD INTEREST INCOME-2006",
        ),
        "head_trusts_acc": (
            "ER40929",
            "ACCURACY OF HD INCOME FROM TRUSTS-2006",
        ),
        "wife_rent_acc": ("ER40936", "ACCURACY OF WIFE RENT INCOME-2006"),
        "wife_dividends_acc": ("ER40938", "ACCURACY OF WIFE DIVIDENDS-2006"),
        "wife_interest_acc": (
            "ER40940",
            "ACCURACY OF WIFE INTEREST INCOME-2006",
        ),
        "wife_trusts_acc": (
            "ER40942",
            "ACCURACY OF WF INCOME FROM TRUSTS-2006",
        ),
        "ofum_asset_acc": ("ER40998", "ACCURACY OF OTR FU MEMBR ASSET Y-2006"),
    },
    2009: {
        "head_ss_acc": ("ER46930", "ACCURACY OF HEAD SOCIAL SECURITY-2008"),
        "wife_ss_acc": ("ER46932", "ACCURACY OF WIFE SOCIAL SECURITY-2008"),
        "ofum_ss_acc": ("ER46934", "ACCURACY OF OFUM SOCIAL SECURITY-2008"),
        "head_ssi_acc": ("ER46855", "ACCURACY OF HEAD SSI-2008"),
        "wife_ssi_acc": ("ER46883", "ACCURACY OF WIFE SSI-2008"),
        "ofum_ssi_acc": ("ER46911", "ACCURACY OF OTR FU MEMBERS SSI-2008"),
        "head_rent_acc": ("ER46831", "ACCURACY OF HEAD RENT INCOME-2008"),
        "head_dividends_acc": ("ER46833", "ACCURACY OF HEAD DIVIDENDS-2008"),
        "head_interest_acc": (
            "ER46835",
            "ACCURACY OF HEAD INTEREST INCOME-2008",
        ),
        "head_trusts_acc": (
            "ER46837",
            "ACCURACY OF HD INCOME FROM TRUSTS-2008",
        ),
        "wife_rent_acc": ("ER46844", "ACCURACY OF WIFE RENT INCOME-2008"),
        "wife_dividends_acc": ("ER46846", "ACCURACY OF WIFE DIVIDENDS-2008"),
        "wife_interest_acc": (
            "ER46848",
            "ACCURACY OF WIFE INTEREST INCOME-2008",
        ),
        "wife_trusts_acc": (
            "ER46850",
            "ACCURACY OF WF INCOME FROM TRUSTS-2008",
        ),
        "ofum_asset_acc": ("ER46906", "ACCURACY OF OTR FU MEMBR ASSET Y-2008"),
    },
    2011: {
        "head_ss_acc": ("ER52338", "ACCURACY OF HEAD SOCIAL SECURITY-2010"),
        "wife_ss_acc": ("ER52340", "ACCURACY OF WIFE SOCIAL SECURITY-2010"),
        "ofum_ss_acc": ("ER52342", "ACCURACY OF OFUM SOCIAL SECURITY-2010"),
        "head_ssi_acc": ("ER52263", "ACCURACY OF HEAD SSI-2010"),
        "wife_ssi_acc": ("ER52291", "ACCURACY OF WIFE SSI-2010"),
        "ofum_ssi_acc": ("ER52319", "ACCURACY OF OTR FU MEMBERS SSI-2010"),
        "head_rent_acc": ("ER52239", "ACCURACY OF HEAD RENT INCOME-2010"),
        "head_dividends_acc": ("ER52241", "ACCURACY OF HEAD DIVIDENDS-2010"),
        "head_interest_acc": (
            "ER52243",
            "ACCURACY OF HEAD INTEREST INCOME-2010",
        ),
        "head_trusts_acc": (
            "ER52245",
            "ACCURACY OF HD INCOME FROM TRUSTS-2010",
        ),
        "wife_rent_acc": ("ER52252", "ACCURACY OF WIFE RENT INCOME-2010"),
        "wife_dividends_acc": ("ER52254", "ACCURACY OF WIFE DIVIDENDS-2010"),
        "wife_interest_acc": (
            "ER52256",
            "ACCURACY OF WIFE INTEREST INCOME-2010",
        ),
        "wife_trusts_acc": (
            "ER52258",
            "ACCURACY OF WF INCOME FROM TRUSTS-2010",
        ),
        "ofum_asset_acc": ("ER52314", "ACCURACY OF OTR FU MEMBR ASSET Y-2010"),
    },
    2013: {
        "head_ss_acc": ("ER58147", "ACCURACY OF HEAD SOCIAL SECURITY-2012"),
        "wife_ss_acc": ("ER58149", "ACCURACY OF WIFE SOCIAL SECURITY-2012"),
        "ofum_ss_acc": ("ER58151", "ACCURACY OF OFUM SOCIAL SECURITY-2012"),
        "head_ssi_acc": ("ER58064", "ACCURACY OF HEAD SSI-2012"),
        "wife_ssi_acc": ("ER58094", "ACCURACY OF WIFE SSI-2012"),
        "ofum_ssi_acc": ("ER58128", "ACCURACY OF OTR FU MEMBERS SSI-2012"),
        "head_rent_acc": ("ER58040", "ACCURACY OF HEAD RENT INCOME-2012"),
        "head_dividends_acc": ("ER58042", "ACCURACY OF HEAD DIVIDENDS-2012"),
        "head_interest_acc": (
            "ER58044",
            "ACCURACY OF HEAD INTEREST INCOME-2012",
        ),
        "head_trusts_acc": (
            "ER58046",
            "ACCURACY OF HD INCOME FROM TRUSTS-2012",
        ),
        "wife_rent_acc": ("ER58053", "ACCURACY OF WIFE RENT INCOME-2012"),
        "wife_dividends_acc": ("ER58055", "ACCURACY OF WIFE DIVIDENDS-2012"),
        "wife_interest_acc": (
            "ER58057",
            "ACCURACY OF WIFE INTEREST INCOME-2012",
        ),
        "wife_trusts_acc": (
            "ER58059",
            "ACCURACY OF WF INCOME FROM TRUSTS-2012",
        ),
        "ofum_asset_acc": ("ER58123", "ACCURACY OF OTR FU MEMBR ASSET Y-2012"),
    },
}

#: Reported asset income the primary income concept replaces (plan field
#: F4): head and wife rent, dividends, interest, trusts/royalties and the
#: asset part of unincorporated-business income, and the OFUM total.
ASSET_INCOME_CONCEPTS: tuple[str, ...] = (
    "head_rent",
    "head_dividends",
    "head_interest",
    "head_trusts",
    "head_business_asset",
    "wife_rent",
    "wife_dividends",
    "wife_interest",
    "wife_trusts",
    "wife_business_asset",
    "ofum_asset",
)
#: Head and wife earned-income items that, with the ten head and wife asset
#: items, make up head and wife taxable income. head_farm is the
#: codebook's "Head's and Wife's Income from Farming", which "includes both
#: labor and asset portions"; its asset portion is not separated.
HW_EARNED_CONCEPTS: tuple[str, ...] = (
    "head_labor",
    "wife_labor",
    "head_farm",
    "head_business_labor",
    "wife_business_labor",
)
#: Accuracy flags read with the income items (raw codes, 0 = actual).
ACCURACY_CONCEPTS: tuple[str, ...] = tuple(
    f"{concept}_acc"
    for concept in (
        "head_ss",
        "wife_ss",
        "ofum_ss",
        "head_ssi",
        "wife_ssi",
        "ofum_ssi",
        "head_rent",
        "head_dividends",
        "head_interest",
        "head_trusts",
        "wife_rent",
        "wife_dividends",
        "wife_interest",
        "wife_trusts",
        "ofum_asset",
    )
)
#: Social Security of the head, the wife and all OFUMs together.
SOCIAL_SECURITY_CONCEPTS: tuple[str, ...] = ("head_ss", "wife_ss", "ofum_ss")
#: SSI of the head, the wife and all OFUMs together.
SSI_CONCEPTS: tuple[str, ...] = ("head_ssi", "wife_ssi", "ofum_ssi")
#: The seven aggregates the codebook sums into TOTAL FAMILY INCOME.
FAMILY_INCOME_AGGREGATES: tuple[str, ...] = (
    "hw_taxable",
    "hw_transfer",
    "ofum_taxable",
    "ofum_transfer",
    "head_ss",
    "wife_ss",
    "ofum_ss",
)
_HW_TRANSFER_COMMON: tuple[str, ...] = (
    "head_tanf",
    "head_ssi",
    "head_other_welfare",
    "head_va_pension",
    "head_retirement_pensions",
    "head_annuities",
    "head_other_retirement",
    "head_unemployment",
    "head_workers_comp",
    "head_child_support",
    "head_alimony",
    "head_help_relatives",
    "head_help_others",
    "head_misc_transfers",
    "wife_tanf",
    "wife_ssi",
    "wife_other_welfare",
    "wife_unemployment",
    "wife_workers_comp",
    "wife_child_support",
    "wife_help_relatives",
    "wife_help_others",
    "wife_misc_transfers",
)
#: Head and wife transfer items per wave (the 2013 file splits the wife's
#: retirement income and adds head and wife IRAs).
HW_TRANSFER_COMPONENTS: dict[int, tuple[str, ...]] = {
    **{
        wave: (*_HW_TRANSFER_COMMON, "wife_retirement_annuities")
        for wave in (2005, 2007, 2009, 2011)
    },
    2013: (
        *_HW_TRANSFER_COMMON,
        "head_iras",
        "wife_retirement_pensions",
        "wife_annuities",
        "wife_iras",
        "wife_other_retirement",
    ),
}
#: OFUM transfer items (every wave).
OFUM_TRANSFER_COMPONENTS: tuple[str, ...] = (
    "ofum_tanf",
    "ofum_ssi",
    "ofum_other_welfare",
    "ofum_va_pension",
    "ofum_retirement_annuities",
    "ofum_unemployment",
    "ofum_workers_comp",
    "ofum_child_support",
    "ofum_help_relatives",
    "ofum_misc_transfers",
)
#: Items whose codebook documents a loss or a negative balance
#: ("Actual loss", "Actual amount of negative net worth", ...), checked
#: 2026-09-24 against the 2005-2013 family codebooks. Every other amount
#: must be non-negative.
MAY_BE_NEGATIVE: frozenset[str] = frozenset(
    {
        "head_rent",
        "wife_rent",
        "head_business_asset",
        "wife_business_asset",
        "hw_taxable",
        "head_farm",
        "ofum_labor",
        "ofum_asset",
        "ofum_taxable",
        "total_family_income",
        "wealth1",
        "wealth2",
        "home_equity",
        "vehicles",
        "checking_saving",
        "stocks",
        "other_assets",
        "farm_business",
        "other_real_estate",
    }
)
#: The asset values WEALTH1 sums, per wave (codebook definitions of
#: ER46968, ER52392 and ER58209).
WEALTH1_ASSETS: dict[int, tuple[str, ...]] = {
    2009: (
        "farm_business",
        "checking_saving",
        "other_real_estate",
        "stocks",
        "vehicles",
        "other_assets",
        "ira_annuity",
    ),
    2011: (
        "farm_business",
        "checking_saving",
        "other_real_estate",
        "stocks",
        "vehicles",
        "other_assets",
        "ira_annuity",
    ),
    2013: (
        "farm_business_asset",
        "checking_saving",
        "other_real_estate_asset",
        "stocks",
        "vehicles",
        "other_assets",
        "ira_annuity",
    ),
}
#: The debts WEALTH1 nets out, per wave.
WEALTH1_DEBTS: dict[int, tuple[str, ...]] = {
    2009: ("other_debt",),
    2011: (
        "credit_card_debt",
        "student_loan_debt",
        "medical_debt",
        "legal_debt",
        "family_loan_debt",
    ),
    2013: (
        "farm_business_debt",
        "other_real_estate_debt",
        "credit_card_debt",
        "student_loan_debt",
        "medical_debt",
        "legal_debt",
        "family_loan_debt",
        "other_debt",
    ),
}

#: Wave suffix carried by each wave's wealth labels.
_WEALTH_LABEL_SUFFIX: dict[int, str] = {2009: "09", 2011: "11", 2013: "2013"}
#: Sentinel and code domains from the codebooks (2011: ER47316-ER47319).
_AGE_NA = 999
_NO_WIFE = 0
_SEX_CODES: dict[int, str] = {1: "male", 2: "female"}
_WEALTH_ACC_CODES = (0, 1)
_INCOME_ACC_RANGE = (0, 9)
_FU_SIZE_RANGE = (1, 20)
_AGE_RANGE = (1, 120)
_NON_AMOUNT = frozenset(
    {
        "interview",
        "fu_size",
        "head_age",
        "head_sex",
        "wife_age",
        "n_children",
        "census_needs_standard",
        "wealth1_acc",
        *ACCURACY_CONCEPTS,
    }
)
#: Reconciliation tolerance in dollars (reported alongside exact matches).
RECONCILIATION_TOLERANCE = 10


class WealthSupplementNotStagedError(FileNotFoundError):
    """A wave's wealth composites live in a PSID supplement not staged."""


class WealthSupplementNotAdjudicatedError(ValueError):
    """A supplement is staged but no label table has been adjudicated."""


def _normalized(label: str) -> str:
    return " ".join(str(label).split())


def income_variables(wave: int) -> dict[str, tuple[str, str]]:
    """The adjudicated ``{concept: (variable, label)}`` income table."""

    wave = int(wave)
    if wave not in _INCOME_VARS:
        raise ValueError(
            f"Wave {wave} is outside the resolved income waves "
            f"{INCOME_WAVES}."
        )
    return {**_INCOME_VARS[wave], **_ACCURACY_VARS[wave]}


def wealth_variables(wave: int) -> dict[str, tuple[str, str]]:
    """The adjudicated ``{concept: (variable, label)}`` wealth table."""

    wave = int(wave)
    if wave in WEALTH_SUPPLEMENT_WAVES:
        raise WealthSupplementNotAdjudicatedError(
            f"Wave {wave}: WEALTH1 is in a PSID wealth supplement file; no "
            "label table has been adjudicated for it (see "
            "read_family_wealth)."
        )
    if wave not in _WEALTH_VARS:
        raise ValueError(
            f"Wave {wave} is outside the resolved wealth waves "
            f"{WEALTH_WAVES}."
        )
    return dict(_WEALTH_VARS[wave])


def _verify_table(
    labels: Mapping[str, str],
    table: Mapping[str, tuple[str, str]],
    wave: int,
    *,
    suffix_check: str,
) -> None:
    by_label: dict[str, list[str]] = {}
    for name, label in labels.items():
        by_label.setdefault(_normalized(label), []).append(name)
    for concept, (var, label) in table.items():
        family._verified(dict(labels), var, label, wave)
        holders = sorted(by_label.get(_normalized(label), []))
        if holders != [var]:
            raise ValueError(
                f"family {wave}: label {label!r} ({concept}) is carried by "
                f"{holders}; expected only {var}. The release layout may "
                "have changed."
            )
        normalized = _normalized(labels[var])
        if suffix_check == "income":
            match = re.search(r"-((19|20)\d{2})$", normalized)
            if match and int(match.group(1)) != wave - 1:
                raise ValueError(
                    f"family {wave}: label {normalized!r} carries income "
                    f"year {match.group(1)}, expected {wave - 1}."
                )
        else:
            token = _WEALTH_LABEL_SUFFIX[wave]
            if not normalized.endswith(f" {token}"):
                raise ValueError(
                    f"family {wave}: wealth label {normalized!r} does not "
                    f"end with the wave token {token!r}."
                )


def _read_columns(
    sps_path: Path, txt_path: Path, names: list[str], nrows: int | None
) -> pd.DataFrame:
    layout = psid.parse_sps_layout(sps_path).set_index("name")
    missing = [name for name in names if name not in layout.index]
    if missing:
        raise KeyError(f"Column(s) {missing} not found in {sps_path} layout")
    colspecs = [
        (int(layout.loc[name, "start"]) - 1, int(layout.loc[name, "end"]))
        for name in names
    ]
    return pd.read_fwf(
        txt_path,
        colspecs=colspecs,
        names=names,
        header=None,
        nrows=nrows,
        dtype="int64",
    )


def _check_amounts(frame: pd.DataFrame, concepts, context: str) -> None:
    for concept in concepts:
        if concept in _NON_AMOUNT or concept in MAY_BE_NEGATIVE:
            continue
        if (frame[concept] < 0).any():
            raise ValueError(
                f"{context}: negative {concept}, which the codebook does "
                "not document as a loss"
            )


def _decode_demographics(frame: pd.DataFrame, wave: int) -> None:
    context = f"family {wave}"
    low, high = _FU_SIZE_RANGE
    if not frame["fu_size"].between(low, high).all():
        raise ValueError(f"{context}: # IN FU outside {low}-{high}")
    if (frame["n_children"] < 0).any() or (
        frame["n_children"] >= frame["fu_size"]
    ).any():
        raise ValueError(
            f"{context}: # CHILDREN IN FU negative or not below # IN FU"
        )
    sexes = set(int(code) for code in pd.unique(frame["head_sex"]))
    if not sexes <= set(_SEX_CODES):
        raise ValueError(
            f"{context}: undocumented SEX OF HEAD code(s) "
            f"{sorted(sexes - set(_SEX_CODES))}"
        )
    lo_age, hi_age = _AGE_RANGE
    head_age = frame["head_age"]
    if not (head_age.between(lo_age, hi_age) | (head_age == _AGE_NA)).all():
        raise ValueError(f"{context}: undocumented AGE OF HEAD code")
    wife_age = frame["wife_age"]
    if not (
        wife_age.between(lo_age, hi_age) | wife_age.isin([_NO_WIFE, _AGE_NA])
    ).all():
        raise ValueError(f"{context}: undocumented AGE OF WIFE code")
    if (frame["census_needs_standard"] <= 0).any():
        raise ValueError(f"{context}: non-positive CENSUS NEEDS STANDARD")
    frame["head_sex"] = frame["head_sex"].map(_SEX_CODES).astype("string")
    frame["wife_present"] = (wife_age != _NO_WIFE).astype(bool)
    frame["head_age"] = head_age.astype("Int64").mask(head_age == _AGE_NA)
    frame["wife_age"] = wife_age.astype("Int64").mask(
        wife_age.isin([_NO_WIFE, _AGE_NA])
    )


def read_family_income(
    wave: int,
    *,
    data_dir: Path | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read one wave's label-verified family income detail.

    Returns one row per responding family with ``wave``, ``income_year``
    (``wave - 1``), ``interview`` and every concept of
    :func:`income_variables` under its concept name, plus
    ``wife_present`` (``AGE OF WIFE`` not 0). ``head_age`` and
    ``wife_age`` are nullable integers (code 999 "DK; NA" and, for the
    wife, 0 "no Wife/'Wife' in FU" become ``<NA>``); ``head_sex`` is
    ``"male"``/``"female"``. Amounts are whole dollars as recorded.
    """

    table = income_variables(wave)
    wave = int(wave)
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    _verify_table(labels, table, wave, suffix_check="income")
    names = [var for var, _ in table.values()]
    raw = _read_columns(sps_path, txt_path, names, nrows)
    frame = pd.DataFrame(
        {concept: raw[var] for concept, (var, _) in table.items()}
    )
    context = f"family {wave}"
    _check_amounts(frame, table, context)
    for concept in ACCURACY_CONCEPTS:
        if not frame[concept].between(*_INCOME_ACC_RANGE).all():
            raise ValueError(
                f"{context}: {concept} outside the accuracy codes "
                f"{_INCOME_ACC_RANGE}"
            )
    if frame["interview"].duplicated().any():
        raise ValueError(f"{context}: duplicate interview numbers")
    _decode_demographics(frame, wave)
    frame.insert(0, "income_year", wave - 1)
    frame.insert(0, "wave", wave)
    return frame.reset_index(drop=True)


def wealth_supplement_status(
    wave: int, *, data_dir: Path | None = None
) -> dict[str, object]:
    """Where a supplement wave's wealth file would be staged, and whether.

    The expected location is ``<PSID data dir>/wealth/<wave>/`` holding one
    ``.sps`` setup and one ``.txt`` data file, the family-file staging
    convention. Nothing is read.
    """

    wave = int(wave)
    if wave not in WEALTH_SUPPLEMENT_WAVES:
        raise ValueError(
            f"Wave {wave} is not a supplement wave {WEALTH_SUPPLEMENT_WAVES}"
        )
    directory = psid._resolve_data_dir(data_dir) / "wealth" / str(wave)
    files = (
        sorted(p.name for p in directory.iterdir())
        if (directory.is_dir())
        else []
    )
    sps = [name for name in files if name.lower().endswith(".sps")]
    txt = [name for name in files if name.lower().endswith(".txt")]
    return {
        "wave": wave,
        "expected_directory": str(directory),
        "files": files,
        "staged": len(sps) == 1 and len(txt) == 1,
    }


def _refuse_supplement_wave(wave: int, data_dir: Path | None) -> None:
    sps_path, _ = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    carriers = sorted(
        name for name, label in labels.items() if "WEALTH" in label.upper()
    )
    if carriers:
        raise ValueError(
            f"family {wave}: the family file now carries WEALTH labels "
            f"{carriers[:4]}; the supplement premise of this reader no "
            "longer holds and the wave needs a label adjudication."
        )
    status = wealth_supplement_status(wave, data_dir=data_dir)
    if not status["staged"]:
        raise WealthSupplementNotStagedError(
            f"PSID {wave} wealth supplement not staged. The {wave} family "
            "file carries no WEALTH composite (no label contains 'WEALTH'); "
            f"PSID released the {wave} imputed wealth composites, including "
            "WEALTH1, as a separate wealth supplement data file. Missing: "
            f"one .sps setup file and one .txt data file of the {wave} "
            f"wealth supplement under {status['expected_directory']} "
            f"(found {status['files'] or 'no directory'}). The file is "
            "login-gated at the PSID Data Center (simba.isr.umich.edu; "
            "see psid-data/README.md) and must be downloaded by Max; its "
            "exact PSID file name and ID were not verified. Nothing was "
            "read."
        )
    raise WealthSupplementNotAdjudicatedError(
        f"PSID {wave} wealth supplement files are staged at "
        f"{status['expected_directory']} ({status['files']}), but no label "
        "table has been adjudicated for them: verify the WEALTH1 label, "
        "its components and the interview-number link, then add the wave "
        "to this module's wealth tables. Nothing was read."
    )


def read_family_wealth(
    wave: int,
    *,
    data_dir: Path | None = None,
    nrows: int | None = None,
) -> pd.DataFrame:
    """Read one wave's label-verified imputed wealth composites.

    Waves 2009, 2011 and 2013 come from the family file: one row per
    family with ``wave``, ``interview``, ``wealth1`` (imputed wealth
    excluding home equity), ``wealth1_acc`` (0 not imputed, 1 imputed),
    ``wealth2``, ``home_equity`` and the WEALTH1 asset and debt components
    of :data:`WEALTH1_ASSETS` and :data:`WEALTH1_DEBTS`.

    Waves 2005 and 2007 are refused: :class:`WealthSupplementNotStagedError`
    names the missing supplement files when they are not staged, and
    :class:`WealthSupplementNotAdjudicatedError` refuses staged files that
    have no adjudicated label table.
    """

    wave = int(wave)
    if wave in WEALTH_SUPPLEMENT_WAVES:
        _refuse_supplement_wave(wave, data_dir)
    table = wealth_variables(wave)
    sps_path, txt_path = family._family_paths(wave, data_dir)
    labels = psid.parse_sps_labels(sps_path)
    interview_var, interview_label = _INCOME_VARS[wave]["interview"]
    _verify_table(
        labels,
        {"interview": (interview_var, interview_label)},
        wave,
        suffix_check="income",
    )
    _verify_table(labels, table, wave, suffix_check="wealth")
    names = [interview_var, *(var for var, _ in table.values())]
    raw = _read_columns(sps_path, txt_path, names, nrows)
    frame = pd.DataFrame({"interview": raw[interview_var]})
    for concept, (var, _) in table.items():
        frame[concept] = raw[var]
    context = f"family {wave} wealth"
    _check_amounts(frame, table, context)
    acc = set(int(code) for code in pd.unique(frame["wealth1_acc"]))
    if not acc <= set(_WEALTH_ACC_CODES):
        raise ValueError(
            f"{context}: undocumented WEALTH1 accuracy code(s) "
            f"{sorted(acc - set(_WEALTH_ACC_CODES))}"
        )
    if frame["interview"].duplicated().any():
        raise ValueError(f"{context}: duplicate interview numbers")
    frame.insert(0, "wave", wave)
    return frame.reset_index(drop=True)


def _identity_counts(
    observed: pd.Series, expected: pd.Series
) -> dict[str, int]:
    gap = (observed.astype("int64") - expected.astype("int64")).abs()
    return {
        "n_families": int(len(gap)),
        "n_exact": int((gap == 0).sum()),
        "n_within_tolerance": int((gap <= RECONCILIATION_TOLERANCE).sum()),
        "n_beyond_tolerance": int((gap > RECONCILIATION_TOLERANCE).sum()),
    }


def reconcile_family_income(frame: pd.DataFrame) -> dict[str, dict]:
    """Count families whose income components do not add up, per wave.

    Identities (codebook definitions):

    * ``total_family_income`` = the seven aggregates of
      :data:`FAMILY_INCOME_AGGREGATES`;
    * ``hw_taxable`` = head and wife labor income, head (and wife) farm
      income, the head's and wife's labor part of business income and the
      ten head and wife asset items of :data:`ASSET_INCOME_CONCEPTS`
      (found on the staged files: ``LABOR INCOME OF HEAD`` excludes the
      farm and business-labor items, which the taxable total adds);
    * ``hw_transfer`` = the head and wife transfer items of
      :data:`HW_TRANSFER_COMPONENTS`;
    * ``ofum_taxable`` = ``ofum_labor + ofum_asset``;
    * ``ofum_transfer`` = the items of :data:`OFUM_TRANSFER_COMPONENTS`.

    Returns ``{str(wave): {identity: counts}}`` where counts give the
    number of families, exact matches, matches within
    :data:`RECONCILIATION_TOLERANCE` dollars and misses beyond it. Counts
    only: no threshold is involved.
    """

    out: dict[str, dict] = {}
    hw_assets = [c for c in ASSET_INCOME_CONCEPTS if c != "ofum_asset"]
    for wave, rows in frame.groupby("wave", sort=True):
        wave = int(wave)
        out[str(wave)] = {
            "total_family_income": _identity_counts(
                rows["total_family_income"],
                rows[list(FAMILY_INCOME_AGGREGATES)].sum(axis=1),
            ),
            "hw_taxable": _identity_counts(
                rows["hw_taxable"],
                rows[[*HW_EARNED_CONCEPTS, *hw_assets]].sum(axis=1),
            ),
            "hw_transfer": _identity_counts(
                rows["hw_transfer"],
                rows[list(HW_TRANSFER_COMPONENTS[wave])].sum(axis=1),
            ),
            "ofum_taxable": _identity_counts(
                rows["ofum_taxable"],
                rows[["ofum_labor", "ofum_asset"]].sum(axis=1),
            ),
            "ofum_transfer": _identity_counts(
                rows["ofum_transfer"],
                rows[list(OFUM_TRANSFER_COMPONENTS)].sum(axis=1),
            ),
        }
    return out


def reconcile_wealth1(frame: pd.DataFrame) -> dict[str, dict]:
    """Count families whose WEALTH1 and WEALTH2 identities fail, per wave.

    ``wealth1`` = the assets of :data:`WEALTH1_ASSETS` minus the debts of
    :data:`WEALTH1_DEBTS`; ``wealth2`` = ``wealth1 + home_equity``. Counts
    only.
    """

    out: dict[str, dict] = {}
    for wave, rows in frame.groupby("wave", sort=True):
        wave = int(wave)
        assets = rows[list(WEALTH1_ASSETS[wave])].sum(axis=1)
        debts = rows[list(WEALTH1_DEBTS[wave])].sum(axis=1)
        out[str(wave)] = {
            "wealth1": _identity_counts(rows["wealth1"], assets - debts),
            "wealth2": _identity_counts(
                rows["wealth2"], rows["wealth1"] + rows["home_equity"]
            ),
        }
    return out
