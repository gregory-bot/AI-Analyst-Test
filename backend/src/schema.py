"""Extraction schema: the contract between the AI step and the deterministic steps.

Rule of thumb: the model only *transcribes and reads* (numbers exactly as printed,
facts with a source reference). All arithmetic, sign conventions, ratio
calculations and rule-based scoring happen in plain Python afterwards, so every
number in the template can be traced and re-computed.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Financial statements – one value per year, exactly as printed (USD '000)     #
# --------------------------------------------------------------------------- #
class Years(Strict):
    """Bracketed figures are negative. Use null for '—', '(−)' or blank cells."""
    y2021: Optional[float]
    y2022: Optional[float]
    y2023: Optional[float]
    y2024: Optional[float]
    y2025F: Optional[float]


class IncomeStatement(Strict):
    revenue: Years
    cost_of_sales: Years
    gross_profit: Years
    other_operating_income: Years
    selling_distribution_expenses: Years
    general_admin_expenses: Years
    technology_platform_costs: Years
    ecl_impairment: Years
    ebitda: Years
    depreciation: Years
    amortization: Years
    ebit: Years
    finance_income: Years
    finance_costs: Years
    net_fx_gain_loss: Years
    profit_before_tax: Years
    income_tax: Years
    profit_after_tax: Years
    gross_margin_pct: Years = Field(description="As a decimal, e.g. 34% -> 0.34")


class BalanceSheet(Strict):
    ppe_net: Years
    right_of_use_assets: Years
    intangible_assets: Years
    deferred_tax_other_nca: Years
    total_non_current_assets: Years
    cash: Years
    trade_other_receivables: Years
    loan_receivables_current: Years
    loan_receivables_non_current: Years
    inventories: Years
    other_current_assets: Years
    total_current_assets: Years
    total_assets: Years
    share_capital_premium: Years
    retained_earnings: Years
    total_equity: Years
    borrowings_long_term: Years
    lease_liabilities_long_term: Years
    deferred_income_other_ncl: Years
    total_non_current_liabilities: Years
    borrowings_short_term: Years
    trade_payables_accruals: Years
    current_tax_liabilities: Years
    lease_liabilities_short_term: Years
    other_current_liabilities: Years
    total_current_liabilities: Years
    total_liabilities: Years
    total_equity_and_liabilities: Years


class CashFlow(Strict):
    profit_before_tax: Years
    depreciation_amortization: Years
    net_finance_costs_paid: Years
    ecl_non_cash: Years
    change_trade_receivables: Years
    change_inventories: Years
    change_loan_receivables: Years
    change_payables_other: Years
    income_taxes_paid: Years
    net_cash_operating: Years
    purchase_ppe: Years
    purchase_intangibles: Years
    net_cash_investing: Years
    net_proceeds_borrowings: Years
    proceeds_share_issues: Years
    lease_payments: Years
    dividends_paid: Years
    net_cash_financing: Years
    net_change_in_cash: Years
    cash_beginning: Years
    cash_end: Years


class FinancialStatements(Strict):
    currency: str
    units: str = Field(description="e.g. USD '000")
    auditor: Optional[str]
    accounting_standard: Optional[str]
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlow
    revenue_mix_notes: str = Field(description="Revenue composition note, verbatim ranges")


# --------------------------------------------------------------------------- #
# Memo                                                                         #
# --------------------------------------------------------------------------- #
class Fact(Strict):
    value: str
    source: str = Field(description="Document + section, e.g. 'Memo p.1 Introduction'")


class Money(Strict):
    usd: Optional[float] = Field(description="Full USD, e.g. 6000000")
    source: str


class Person(Strict):
    name: str
    role: str
    experience: str
    prior_employers: str


class Shareholder(Strict):
    name: str
    pct: Optional[float] = Field(description="Decimal, e.g. 0.25")
    type: str


class UseOfProceeds(Strict):
    instrument: Literal["senior_secured_debt", "equity", "other"]
    usd: float
    purpose: str


class CountryTierClaim(Strict):
    country: str
    tier_claimed_in_memo: str


class MemoTableRow(Strict):
    year: str
    revenue: Optional[float]
    ebitda: Optional[float]
    net_profit: Optional[float]
    gross_margin_pct: Optional[float]
    total_assets: Optional[float]
    equity: Optional[float]
    debt: Optional[float]
    loan_book: Optional[float]
    cash: Optional[float]


class Memo(Strict):
    company_name: Fact
    business_description: Fact = Field(description="2-3 sentence factual summary")
    sector: Fact = Field(description="Concise sector label, e.g. 'Agri-fintech (input finance)'")
    legal_form: Fact
    founded: Fact
    headquarters: Fact
    operating_countries: list[str]
    planned_countries: list[str]
    primary_country: str = Field(description="Largest market, spelled as in an English country list")
    funding_headline: Money = Field(description="Total raise as stated in the introduction")
    funding_total_use_of_proceeds: Money = Field(description="Total per use-of-proceeds section")
    funding_headline_instrument_wording: Fact = Field(description="Verbatim instrument wording in intro, e.g. 'senior debt'")
    use_of_proceeds: list[UseOfProceeds]
    security_package: Fact
    collateral_liquidation: Fact
    loan_product: Fact = Field(description="Tenor, interest, repayment mechanism")
    management: list[Person]
    team_tenure: Fact
    board_composition: Fact
    governance_practices: Fact
    reputation: Fact
    shareholders: list[Shareholder]
    lenders_and_co_investors: Fact
    deal_source: Optional[Fact] = Field(description="null if the memo does not say how the deal was sourced")
    founders_named: Fact = Field(description="Who the memo says the founders are; say 'not named' if not explicit")
    clients_reached: Fact
    women_pct: Optional[float]
    youth_pct: Optional[float]
    women_reached: Optional[float]
    youth_reached: Optional[float]
    climate: Fact = Field(description="Climate-related product features and share of loans")
    impact_metrics: list[str]
    sdgs: list[str]
    market_size: Fact
    competitive_position: Fact
    growth_plans: Fact
    customer_value_proposition: Fact
    country_tier_claims: list[CountryTierClaim]
    fx_rate_claim: Fact
    capital_efficiency_claim: Fact
    auditor_claim: Fact
    memo_financial_table: list[MemoTableRow] = Field(description="Selected Financials table, USD '000, as printed")


# --------------------------------------------------------------------------- #
# Qualitative screen – judgement criteria only (quant criteria are rule-based) #
# --------------------------------------------------------------------------- #
QualCriterion = Literal[
    "deal_origination", "breadth", "in_market", "team_churn", "reputation",
    "governance", "stakeholders", "customer_ltv", "customer_focus",
    "competitive_moat", "new_products_markets", "funding_requirement", "market_size",
]


class QualScore(Strict):
    criterion: QualCriterion
    score: Optional[int] = Field(description="1, 2 or 3 per the guide; null when the documents give no information")
    rationale: str = Field(description="One or two sentences tied to the guide wording")
    evidence: str = Field(description="Document + section the score relies on")
    dd_question: str = Field(description="What due diligence must confirm before relying on this score")


class Screen(Strict):
    local_founder: Literal["Yes", "No", "Maybe"]
    local_founder_rationale: str
    climate_alignment: Literal["Yes, Adaptation", "Yes, Mitigation", "Maybe", "No"]
    climate_rationale: str
    two_x_alignment: Literal["Yes", "No", "Maybe"]
    two_x_rationale: str = Field(description="Assess a) ownership b) leadership c) employment d) supply chain e) products")
    impact_toc: Literal["Yes", "No", "Maybe"]
    impact_rationale: str
    security_workable: Literal["Yes", "No", "Maybe"]
    security_rationale: str
    qualitative_scores: list[QualScore]
    key_dd_areas: list[str] = Field(description="5-8 priority due-diligence areas")


class Extraction(Strict):
    financials: FinancialStatements
    memo: Memo
    screen: Screen
