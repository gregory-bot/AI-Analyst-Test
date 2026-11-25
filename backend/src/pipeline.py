"""The 4-step pipeline, shared by the CLI (run.py) and the web API (api.py)."""
from __future__ import annotations

import json
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import extract, populate, score, validate

warnings.filterwarnings("ignore", message="Data Validation extension")  # re-added in populate.py

BACKEND = Path(__file__).resolve().parent.parent
CONFIG = BACKEND / "config" / "field_map.yaml"
REFERENCE = BACKEND / "tests" / "agriwave_reference_extraction.json"

# criterion -> (display label, category)
CRITERIA = {
    "deal_origination": ("Deal Origination", "Team"), "breadth": ("Breadth", "Team"),
    "in_market": ("In Market", "Team"), "team_churn": ("Team Churn", "Team"),
    "reputation": ("Reputation", "Team"), "governance": ("Governance", "Team"),
    "stakeholders": ("Stakeholders", "Team"),
    "customer_ltv": ("Customer LTV", "Business Model"), "revenue_growth": ("Revenue Growth", "Business Model"),
    "profitability": ("Profitability", "Business Model"), "unit_profitability": ("Unit Profitability", "Business Model"),
    "capital_efficiency": ("Capital Efficiency", "Business Model"), "customer_focus": ("Customer Focus", "Business Model"),
    "competitive_moat": ("Competitive Moat", "Business Model"),
    "new_products_markets": ("New Products / Markets", "Ability to Scale"),
    "funding_requirement": ("Funding Requirement", "Ability to Scale"),
    "use_of_leverage": ("Use of Leverage", "Ability to Scale"), "market_size": ("Market Size", "Ability to Scale"),
}
WEIGHTS = {"Team": 0.35, "Business Model": 0.50, "Ability to Scale": 0.15}
STEPS = ["Extract (OpenAI)", "Validate", "Score", "Populate template"]


def run_pipeline(memo: Path, financials: Path, template: Path, out_dir: Path,
                 replay: Path | None = None, on_step: Callable[[int, str], None] = lambda i, m: None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "inputs": f"{memo.name} | {financials.name} | {template.name}"}

    # 1 Extract
    if replay:
        on_step(0, f"Loading saved extraction ({replay.name})")
        x = extract.load(replay)
        meta["mode"] = "demo (saved extraction)" if replay == REFERENCE else f"replay of {replay.name}"
    else:
        on_step(0, f"OpenAI {extract.MODEL} is reading the memo and financial statements")
        x, usage = extract.extract(memo, financials)
        meta |= {"mode": "live", **usage}
    (out_dir / "extraction.json").write_text(x.model_dump_json(indent=2))

    # 2 Validate
    on_step(1, "Checking arithmetic, statement roll-forwards and memo claims")
    gating = populate.gating_table(template)
    flags = validate.run(x, gating)

    # 3 Score
    on_step(2, "Scoring quantitative criteria and merging AI judgement scores")
    debt_ask = sum(u.usd for u in x.memo.use_of_proceeds if u.instrument == "senior_secured_debt")
    eq_raise = sum(u.usd for u in x.memo.use_of_proceeds if u.instrument == "equity")
    rules = score.run(x, debt_ask, eq_raise)

    # 4 Populate
    on_step(3, "Writing the TMS screening template")
    xlsx = out_dir / f"{x.memo.company_name.value.replace(' ', '_')}_TMS_Screening.xlsx"
    fixes = populate.populate(template, xlsx, x, flags, rules, debt_ask, CONFIG, meta)
    (out_dir / "validation_flags.json").write_text(json.dumps([f.dict() for f in flags], indent=2, default=str))

    return _summary(x, flags, rules, fixes, gating, meta, debt_ask, eq_raise, xlsx)


def _summary(x, flags, rules, fixes, gating, meta, debt_ask, eq_raise, xlsx) -> dict:
    """JSON-friendly view of the run for the web UI / console."""
    m, s = x.memo, x.screen
    norm = validate._norm

    scores = [{"criterion": q.criterion, "score": q.score, "method": "AI judgement", "rationale": q.rationale,
               "evidence": q.evidence,
               "dd": "" if q.dd_question.strip().lower() in ("n/a", "none", "-") else q.dd_question}
              for q in s.qualitative_scores]
    scores += [{"criterion": r.criterion, "score": r.score, "method": "Rule-based", "rationale": r.rationale,
                "evidence": r.evidence, "dd": ""} for r in rules]
    for sc in scores:
        sc["label"], sc["category"] = CRITERIA[sc["criterion"]]
    scores.sort(key=lambda sc: list(CRITERIA).index(sc["criterion"]))

    categories, overall = [], 0.0
    for cat, w in WEIGHTS.items():
        vals = [sc["score"] for sc in scores if sc["category"] == cat and sc["score"] is not None]
        pct = sum(vals) / (3 * len(vals)) if vals else 0.0
        overall += w * pct
        categories.append({"name": cat, "weight": w, "pct": pct, "points": sum(vals), "max": 3 * len(vals)})
    band = ("Actively cultivate relationship" if overall > 0.7 else
            "Monitor passively" if overall >= 0.5 else "Do not proceed")

    IS, BS = x.financials.income_statement, x.financials.balance_sheet
    g = lambda ser, y: getattr(ser, y) or 0.0
    metrics = []
    for y in ("y2021", "y2022", "y2023", "y2024", "y2025F"):
        debt = g(BS.borrowings_long_term, y) + g(BS.borrowings_short_term, y)
        metrics.append({
            "year": y[1:], "revenue": g(IS.revenue, y), "gross_margin": g(IS.gross_margin_pct, y),
            "ebitda_reported": g(IS.ebitda, y), "pat_reported": g(IS.profit_after_tax, y),
            "loan_book": g(BS.loan_receivables_current, y) + g(BS.loan_receivables_non_current, y),
            "debt": debt, "equity": g(BS.total_equity, y),
            "debt_to_equity": debt / g(BS.total_equity, y) if g(BS.total_equity, y) else None,
        })

    return {
        "run": meta,
        "company": {
            "name": m.company_name.value, "description": m.business_description.value, "sector": m.sector.value,
            "founded": m.founded.value, "primary_country": m.primary_country,
            "countries": [{"name": c, "status": st, "tier": gating.get(norm(c), "Not listed")}
                          for st, lst in (("Operating", m.operating_countries), ("Planned", m.planned_countries)) for c in lst],
            "management": [p.model_dump() for p in m.management],
            "shareholders": [sh.model_dump() for sh in m.shareholders],
        },
        "funding": {"total": m.funding_total_use_of_proceeds.usd, "debt_ask": debt_ask, "equity": eq_raise,
                    "use_of_proceeds": [u.model_dump() for u in m.use_of_proceeds],
                    "security": m.security_package.value},
        "screen": {
            "impact_toc": s.impact_toc, "impact_rationale": s.impact_rationale,
            "climate": s.climate_alignment, "climate_rationale": s.climate_rationale,
            "two_x": s.two_x_alignment, "two_x_rationale": s.two_x_rationale,
            "local_founder": s.local_founder, "local_founder_rationale": s.local_founder_rationale,
            "security": s.security_workable, "security_rationale": s.security_rationale,
        },
        "scores": scores, "categories": categories, "overall": overall, "band": band,
        "metrics": metrics,
        "flags": [f.dict() for f in flags],
        "flag_counts": dict(Counter(f.severity for f in flags)),
        "key_dd_areas": s.key_dd_areas, "template_fixes": fixes,
        "output_file": xlsx.name,
    }
