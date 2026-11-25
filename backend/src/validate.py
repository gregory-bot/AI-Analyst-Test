"""Step 2 – deterministic validation. No AI: pure arithmetic and rule checks.

Each check yields a Flag. Severity:
  HIGH   - affects a screening input/score or the credit view; must be resolved in DD
  MEDIUM - internal inconsistency in the source documents
  INFO   - passed check (kept so the reviewer can see what was tested)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .schema import Extraction

YEARS = ["y2021", "y2022", "y2023", "y2024", "y2025F"]
LABEL = {y: y[1:] for y in YEARS}
TOL = 1.0  # USD '000 rounding tolerance


@dataclass
class Flag:
    area: str
    check: str
    year: str
    expected: float | str | None
    reported: float | str | None
    severity: str
    note: str

    def dict(self):
        return asdict(self)


def v(series, y):
    x = getattr(series, y)
    return 0.0 if x is None else x


def _cmp(flags, area, check, y, expected, reported, sev, note=""):
    if reported is None:
        flags.append(Flag(area, check, LABEL[y], expected, None, sev, "Figure not reported (blank/dash). " + note))
        return
    ok = abs(expected - reported) <= TOL
    flags.append(Flag(area, check, LABEL[y], round(expected, 2), reported,
                      "INFO" if ok else sev, "OK" if ok else note))


def run(x: Extraction, gating: dict[str, str]) -> list[Flag]:
    f: list[Flag] = []
    IS, BS, CF = x.financials.income_statement, x.financials.balance_sheet, x.financials.cash_flow

    # ---------------- Income statement arithmetic ----------------
    for y in YEARS:
        gp = v(IS.revenue, y) + v(IS.cost_of_sales, y)
        _cmp(f, "P&L", "Gross profit = Revenue - Cost of sales", y, gp, getattr(IS.gross_profit, y), "MEDIUM")
        ebitda = gp + sum(v(s, y) for s in (IS.other_operating_income, IS.selling_distribution_expenses,
                                            IS.general_admin_expenses, IS.technology_platform_costs, IS.ecl_impairment))
        _cmp(f, "P&L", "EBITDA recomputed from line items", y, ebitda, getattr(IS.ebitda, y), "HIGH",
             "Stated EBITDA differs from the sum of line items; downstream EBIT/PBT/PAT inherit the gap. "
             "Template uses line items.")
        ebit = v(IS.ebitda, y) + v(IS.depreciation, y) + v(IS.amortization, y)
        _cmp(f, "P&L", "EBIT = stated EBITDA - D&A", y, ebit, getattr(IS.ebit, y), "MEDIUM")
        pbt = v(IS.ebit, y) + v(IS.finance_income, y) + v(IS.finance_costs, y) + v(IS.net_fx_gain_loss, y)
        _cmp(f, "P&L", "PBT = stated EBIT + finance items", y, pbt, getattr(IS.profit_before_tax, y), "MEDIUM")
        pat = v(IS.profit_before_tax, y) + v(IS.income_tax, y)
        _cmp(f, "P&L", "PAT = stated PBT - tax", y, pat, getattr(IS.profit_after_tax, y), "MEDIUM")
        if v(IS.revenue, y):
            gm = round(gp / v(IS.revenue, y), 2)
            _cmp(f, "P&L", "Gross margin %", y, gm, getattr(IS.gross_margin_pct, y), "MEDIUM")

    # ---------------- Balance sheet arithmetic ----------------
    for y in YEARS:
        nca = sum(v(s, y) for s in (BS.ppe_net, BS.right_of_use_assets, BS.intangible_assets, BS.deferred_tax_other_nca))
        _cmp(f, "Balance sheet", "Non-current assets subtotal", y, nca, getattr(BS.total_non_current_assets, y), "MEDIUM")
        ca_lines = [BS.cash, BS.trade_other_receivables, BS.loan_receivables_current,
                    BS.loan_receivables_non_current, BS.inventories, BS.other_current_assets]
        ca_all = sum(v(s, y) for s in ca_lines)
        ca_excl = ca_all - v(BS.loan_receivables_non_current, y)
        stated_ca = getattr(BS.total_current_assets, y)
        matches = stated_ca is not None and min(abs(stated_ca - ca_all), abs(stated_ca - ca_excl)) <= TOL
        f.append(Flag("Balance sheet", "Current assets subtotal (with or without non-current loans)", LABEL[y],
                      f"{ca_all:g} incl. / {ca_excl:g} excl. NC loans", stated_ca,
                      "INFO" if matches else "MEDIUM",
                      "OK (label says 'incl.' but figure excludes NC loans)" if matches
                      else "Subtotal matches neither definition"))
        ta = nca + ca_all
        _cmp(f, "Balance sheet", "Total assets = sum of asset lines", y, ta, getattr(BS.total_assets, y), "MEDIUM")
        eq = v(BS.share_capital_premium, y) + v(BS.retained_earnings, y)
        _cmp(f, "Balance sheet", "Total equity = share capital + retained earnings", y, eq, getattr(BS.total_equity, y), "MEDIUM")
        ncl = sum(v(s, y) for s in (BS.borrowings_long_term, BS.lease_liabilities_long_term, BS.deferred_income_other_ncl))
        _cmp(f, "Balance sheet", "Non-current liabilities subtotal", y, ncl, getattr(BS.total_non_current_liabilities, y), "MEDIUM")
        cl = sum(v(s, y) for s in (BS.borrowings_short_term, BS.trade_payables_accruals, BS.current_tax_liabilities,
                                   BS.lease_liabilities_short_term, BS.other_current_liabilities))
        _cmp(f, "Balance sheet", "Current liabilities subtotal", y, cl, getattr(BS.total_current_liabilities, y), "MEDIUM")
        _cmp(f, "Balance sheet", "Balance check: stated total assets = stated equity + liabilities", y,
             v(BS.total_assets, y), getattr(BS.total_equity_and_liabilities, y), "HIGH",
             "Balance sheet as published does not balance.")

    # ---------------- Roll-forwards between statements ----------------
    for i, y in enumerate(YEARS[1:], start=1):
        p = YEARS[i - 1]
        _cmp(f, "Roll-forward", "Retained earnings = prior RE + PAT - dividends", y,
             v(BS.retained_earnings, p) + v(IS.profit_after_tax, y) + v(CF.dividends_paid, y),
             getattr(BS.retained_earnings, y), "HIGH",
             "Unexplained movement in retained earnings (no dividends recorded).")
        _cmp(f, "Roll-forward", "Share capital movement = share issue proceeds", y,
             v(BS.share_capital_premium, y) - v(BS.share_capital_premium, p), getattr(CF.proceeds_share_issues, y), "MEDIUM")
        debt = lambda yy: v(BS.borrowings_long_term, yy) + v(BS.borrowings_short_term, yy)
        _cmp(f, "Roll-forward", "Borrowings movement = net borrowing proceeds", y,
             debt(y) - debt(p), getattr(CF.net_proceeds_borrowings, y), "MEDIUM")
        lb = lambda yy: v(BS.loan_receivables_current, yy) + v(BS.loan_receivables_non_current, yy)
        _cmp(f, "Roll-forward", "Loan book movement = CF change in loan receivables", y,
             -(lb(y) - lb(p)), getattr(CF.change_loan_receivables, y), "MEDIUM")
        _cmp(f, "Roll-forward", "Inventory movement = CF change in inventories", y,
             -(v(BS.inventories, y) - v(BS.inventories, p)), getattr(CF.change_inventories, y), "MEDIUM",
             "Sign/amount of inventory movement in cash flow is inconsistent with the balance sheet.")

    # ---------------- Cash flow ----------------
    for y in YEARS:
        cfo = sum(v(s, y) for s in (CF.profit_before_tax, CF.depreciation_amortization, CF.net_finance_costs_paid,
                                    CF.ecl_non_cash, CF.change_trade_receivables, CF.change_inventories,
                                    CF.change_loan_receivables, CF.change_payables_other, CF.income_taxes_paid))
        _cmp(f, "Cash flow", "Operating cash flow = sum of line items", y, cfo, getattr(CF.net_cash_operating, y), "HIGH",
             "Operating cash flow total missing or inconsistent with its line items.")
        actual = v(CF.cash_end, y) - v(CF.cash_beginning, y)
        _cmp(f, "Cash flow", "Net change in cash = closing - opening cash", y, actual, getattr(CF.net_change_in_cash, y), "HIGH")
        implied = cfo + v(CF.net_cash_investing, y) + v(CF.net_cash_financing, y)
        _cmp(f, "Cash flow", "CFO(line items) + CFI + CFF = actual cash movement", y, actual, implied, "HIGH",
             "Cash flow statement does not reconcile to the balance sheet cash movement.")
        _cmp(f, "Cash flow", "CF closing cash = balance sheet cash", y, v(BS.cash, y), getattr(CF.cash_end, y), "MEDIUM")

    # ---------------- Memo vs financial statements ----------------
    fs_lookup = {
        "revenue": lambda y: v(IS.revenue, y), "ebitda": lambda y: v(IS.ebitda, y),
        "net_profit": lambda y: v(IS.profit_after_tax, y), "gross_margin_pct": lambda y: v(IS.gross_margin_pct, y),
        "total_assets": lambda y: v(BS.total_assets, y), "equity": lambda y: v(BS.total_equity, y),
        "debt": lambda y: v(BS.borrowings_long_term, y) + v(BS.borrowings_short_term, y),
        "loan_book": lambda y: v(BS.loan_receivables_current, y) + v(BS.loan_receivables_non_current, y),
        "cash": lambda y: v(BS.cash, y),
    }
    mismatches = 0
    for row in x.memo.memo_financial_table:
        y = "y" + row.year.strip().replace("f", "F")
        if y not in YEARS:
            continue
        for k, fn in fs_lookup.items():
            mv = getattr(row, k)
            if mv is not None and abs(mv - fn(y)) > (0.01 if k == "gross_margin_pct" else TOL):
                mismatches += 1
                _cmp(f, "Memo vs FS", f"Memo table '{k}' vs financial statements", y, fn(y), mv, "HIGH")
    f.append(Flag("Memo vs FS", "Memo selected-financials table agrees to statements (all metrics/years)", "all",
                  0, mismatches, "INFO" if not mismatches else "HIGH",
                  "OK - memo table agrees to the stated (not recomputed) figures" if not mismatches else "See rows above"))

    # ---------------- Memo internal claims ----------------
    m = x.memo
    head, total = m.funding_headline.usd, m.funding_total_use_of_proceeds.usd
    uop_sum = sum(u.usd for u in m.use_of_proceeds)
    debt_ask = sum(u.usd for u in m.use_of_proceeds if u.instrument == "senior_secured_debt")
    eq_ask = sum(u.usd for u in m.use_of_proceeds if u.instrument == "equity")
    f.append(Flag("Memo claims", "Funding ask: headline amount & instrument vs use of proceeds", "-",
                  f"${uop_sum/1e6:.1f}m = ${debt_ask/1e6:.1f}m senior secured debt + ${eq_ask/1e6:.1f}m equity",
                  f"${(head or 0)/1e6:.1f}m '{m.funding_headline_instrument_wording.value}'",
                  "HIGH" if ("debt" in m.funding_headline_instrument_wording.value.lower() and eq_ask > 0)
                  or abs((head or 0) - uop_sum) > 1 else "INFO",
                  f"AHL debt sizing uses ${debt_ask/1e6:.1f}m senior secured debt; equity component (${eq_ask/1e6:.1f}m) "
                  "is not an AHL debt ask and needs a lead equity investor."))

    for c in m.country_tier_claims:
        actual = gating.get(_norm(c.country))
        if actual is None:
            continue
        ok = actual.lower() == c.tier_claimed_in_memo.lower()
        f.append(Flag("Memo claims", f"Country tier for {c.country} vs AHL Country Gating Screen", "-",
                      actual, c.tier_claimed_in_memo, "INFO" if ok else "HIGH",
                      "OK" if ok else "Memo misstates AHL's own country classification; template uses the Gating Screen."))

    pat24 = v(IS.profit_after_tax, "y2024")
    debt24 = fs_lookup["debt"]("y2024")
    eq24 = v(BS.total_equity, "y2024")
    lb24 = fs_lookup["loan_book"]("y2024")
    f.append(Flag("Memo claims", "Capital efficiency ('net margin per $1m capital')", "2024",
                  f"{pat24/(debt24+eq24):.1%} on equity+debt; {pat24/lb24:.1%} on loan book",
                  m.capital_efficiency_claim.value, "HIGH",
                  "Memo figure only holds if 'capital' = loan book. On total capital employed (equity + borrowings) "
                  "the business is in the 17.5-30% band. Screen scores on equity + borrowings."))

    # Interest income plausibility: revenue share of interest vs loan book
    rev24 = v(IS.revenue, "y2024")
    avg_lb = (fs_lookup["loan_book"]("y2023") + lb24) / 2
    implied_yield = 0.65 * rev24 / avg_lb if avg_lb else 0
    f.append(Flag("Plausibility", "Implied annual yield on loan book (interest = 65% of revenue, low end of Note 1)", "2024",
                  "typical agri input loans: 25-60% p.a.", f"{implied_yield:.0%}",
                  "HIGH" if implied_yield > 1 else "INFO",
                  "Interest/fee income of this size cannot be earned on the reported loan book. Either revenue includes "
                  "gross input sales (Note 3 puts input procurement in cost of sales) or the loan book is understated. "
                  "Key DD item: obtain loan-tape and revenue split."))

    f.append(Flag("Memo claims", "FX rate quoted in memo vs template Currency Data (NGN, Dec-2024)", "2024",
                  "1,540 (template)", m.fx_rate_claim.value, "MEDIUM",
                  "Accounts are in USD so no impact on inputs; confirm translation policy and NGN exposure in DD."))
    return f


def _norm(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().strip().lower()
