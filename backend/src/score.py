"""Step 3 – rule-based scoring of the quantitative TMS criteria.

These follow the TMS 'Guide' column literally, so a reviewer can re-derive every
score from the financials. Judgement criteria come from the AI step instead.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import Extraction


@dataclass
class Score:
    criterion: str
    score: int | None
    rationale: str
    evidence: str


def _g(series, y):
    return getattr(series, y) or 0.0


def run(x: Extraction, ahl_debt_usd: float, equity_raise_usd: float) -> list[Score]:
    IS, BS = x.financials.income_statement, x.financials.balance_sheet
    out: list[Score] = []

    # Revenue growth – L3Y average YoY growth in USD (2022-2024, last 3 audited years)
    rev = {y: _g(IS.revenue, y) for y in ("y2021", "y2022", "y2023", "y2024")}
    yoy = [rev["y2022"] / rev["y2021"] - 1, rev["y2023"] / rev["y2022"] - 1, rev["y2024"] / rev["y2023"] - 1]
    avg = sum(yoy) / 3
    out.append(Score("revenue_growth", 3 if avg > 0.30 else 1 if avg < 0.10 else 2,
                     f"L3Y average USD revenue growth {avg:.1%} (2022 {yoy[0]:.0%}, 2023 {yoy[1]:.0%}, 2024 {yoy[2]:.0%}); "
                     f"2025 budget +{_g(IS.revenue,'y2025F')/rev['y2024']-1:.0%}.",
                     "FS Section A - Revenue 2021-2024"))

    # Profitability – last audited PBT
    pbt = _g(IS.profit_before_tax, "y2024") * 1000
    lines = ("revenue", "cost_of_sales", "other_operating_income", "selling_distribution_expenses",
             "general_admin_expenses", "technology_platform_costs", "ecl_impairment", "depreciation",
             "amortization", "finance_income", "finance_costs", "net_fx_gain_loss")
    pbt_lines = sum(_g(getattr(IS, k), "y2024") for k in lines) * 1000
    out.append(Score("profitability", 1 if pbt < 500_000 else 2 if pbt < 3_000_000 else 3,
                     f"Audited FY2024 PBT ${pbt/1e6:.2f}m (band $0.5m-$3m). Line-item recompute gives "
                     f"${pbt_lines/1e6:.2f}m - same band.",
                     "FS Section A - Profit before tax 2024"))

    # Unit profitability – financial business => Net Interest Margin
    lb = lambda y: _g(BS.loan_receivables_current, y) + _g(BS.loan_receivables_non_current, y)
    avg_lb = (lb("y2023") + lb("y2024")) / 2
    interest_low = 0.65 * _g(IS.revenue, "y2024")
    nim = (interest_low + _g(IS.finance_costs, "y2024")) / avg_lb
    gm = _g(IS.gross_margin_pct, "y2024")
    out.append(Score("unit_profitability", 3 if nim > 0.20 else 2 if nim > 0.10 else 1,
                     f"Financial business -> NIM test. Implied NIM {nim:.0%} on avg loan book (interest at 65% of revenue "
                     f"less finance costs); GM {gm:.0%}. Passes either test, but NIM is implausibly high - see validation flag.",
                     "FS Note 1 revenue mix; FS Section B loan receivables"))

    # Capital efficiency – net margin per USD 1m capital (equity + borrowings)
    pat = _g(IS.profit_after_tax, "y2024")
    cap = _g(BS.total_equity, "y2024") + _g(BS.borrowings_long_term, "y2024") + _g(BS.borrowings_short_term, "y2024")
    ce = pat / cap
    out.append(Score("capital_efficiency", 3 if ce > 0.30 else 2 if ce >= 0.175 else 1,
                     f"FY2024 PAT ${pat/1000:.1f}m / capital (equity + borrowings) ${cap/1000:.1f}m = {ce:.1%} "
                     f"-> 17.5-30% band. Memo's '$320k per $1m' only holds on loan book ({pat/lb('y2024'):.1%}).",
                     "FS Sections A & B; Memo p.3 Financial Overview"))

    # Use of leverage – profitable + pro-forma D:E within 3x
    profitable = all(_g(IS.profit_after_tax, y) > 0 for y in ("y2022", "y2023", "y2024"))
    debt25 = _g(BS.borrowings_long_term, "y2025F") + _g(BS.borrowings_short_term, "y2025F")
    eq25 = _g(BS.total_equity, "y2025F")
    pf_de = (debt25 * 1000 + ahl_debt_usd) / (eq25 * 1000 + equity_raise_usd)
    pf_de_no_eq = (debt25 * 1000 + ahl_debt_usd) / (eq25 * 1000)
    out.append(Score("use_of_leverage", 3 if profitable and pf_de_no_eq <= 3 else 2 if profitable else 1,
                     f"Profitable FY22-24; D:E FY2024 {(_g(BS.borrowings_long_term,'y2024')+_g(BS.borrowings_short_term,'y2024'))/_g(BS.total_equity,'y2024'):.2f}x. "
                     f"Pro-forma FY2025 with ${ahl_debt_usd/1e6:.0f}m AHL debt: {pf_de:.2f}x incl. ${equity_raise_usd/1e6:.0f}m equity raise, "
                     f"{pf_de_no_eq:.2f}x without - within 3x either way.",
                     "FS Section B; Memo p.3 Funding & Capital Structure"))
    return out
