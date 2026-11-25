"""Accuracy check: compare a live AI extraction with the hand-checked reference.

    python tests/compare_to_reference.py output/extraction.json

Reports every financial figure that differs (all 5 years x every line item)
plus key memo fields, and a headline accuracy %.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ref = json.loads((ROOT / "agriwave_reference_extraction.json").read_text())
live = json.loads(Path(sys.argv[1]).read_text())

total = wrong = 0
for stmt in ("income_statement", "balance_sheet", "cash_flow"):
    for line, years in ref["financials"][stmt].items():
        for y, rv in years.items():
            lv = live["financials"][stmt][line][y]
            total += 1
            if (rv is None) != (lv is None) or (rv is not None and abs(rv - lv) > 0.5):
                wrong += 1
                print(f"  MISMATCH {stmt}.{line}.{y}: reference={rv} live={lv}")

memo_checks = {
    "primary_country": lambda d: d["memo"]["primary_country"],
    "debt ask": lambda d: sum(u["usd"] for u in d["memo"]["use_of_proceeds"] if u["instrument"] == "senior_secured_debt"),
    "equity ask": lambda d: sum(u["usd"] for u in d["memo"]["use_of_proceeds"] if u["instrument"] == "equity"),
    "headline raise": lambda d: d["memo"]["funding_headline"]["usd"],
    "women %": lambda d: d["memo"]["women_pct"],
    "managers": lambda d: sorted(p["name"] for p in d["memo"]["management"]),
    "tier claims": lambda d: sorted((c["country"], c["tier_claimed_in_memo"]) for c in d["memo"]["country_tier_claims"]),
}
for name, fn in memo_checks.items():
    total += 1
    if fn(ref) != fn(live):
        wrong += 1
        print(f"  MISMATCH memo {name}: reference={fn(ref)} live={fn(live)}")

print(f"\nAccuracy: {total - wrong}/{total} fields match the reference ({(total - wrong) / total:.1%})")
judg = {q["criterion"]: q["score"] for q in live["screen"]["qualitative_scores"]}
refj = {q["criterion"]: q["score"] for q in ref["screen"]["qualitative_scores"]}
diff = {k: (refj.get(k), judg.get(k)) for k in refj if refj.get(k) != judg.get(k)}
print(f"Judgement scores differing from analyst reference (ref, AI): {diff or 'none'}")
