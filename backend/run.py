"""TMS screening automation - command-line entry point.

    python run.py                                  # live: Claude reads the PDFs
    python run.py --replay output/extraction.json  # re-run steps 2-4 on a saved extraction
    python run.py --demo                           # use the bundled reference extraction (no API key)

Pipeline:  1 Extract (Claude) -> 2 Validate (rules) -> 3 Score (rules) -> 4 Populate (Excel)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from src.pipeline import REFERENCE, STEPS, run_pipeline

BACKEND = Path(__file__).resolve().parent
DOCS = BACKEND.parent  # case-study documents live in the project root
load_dotenv(BACKEND / ".env")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--memo", type=Path, default=DOCS / "AgriWave Ltd Investment Memo.pdf")
    ap.add_argument("--financials", type=Path, default=DOCS / "AgriWave Ltd Audited Financial Statements and 2025 budget.pdf")
    ap.add_argument("--template", type=Path, default=DOCS / "2025.12_Screening Template vF.xlsx")
    ap.add_argument("--out", type=Path, default=BACKEND / "output")
    ap.add_argument("--replay", type=Path, help="Skip the AI call and use a saved extraction JSON")
    ap.add_argument("--demo", action="store_true", help="Replay the bundled reference extraction")
    a = ap.parse_args()

    r = run_pipeline(a.memo, a.financials, a.template, a.out,
                     replay=REFERENCE if a.demo else a.replay,
                     on_step=lambda i, msg: print(f"\n[{i + 1}/4] {STEPS[i]}: {msg}"))

    c = r["company"]
    print(f"\n{c['name']} | {c['sector']} | {c['primary_country']}")
    fc = r["flag_counts"]
    print(f"Validation: {len(r['flags'])} checks - {fc.get('INFO', 0)} passed, "
          f"{fc.get('MEDIUM', 0)} medium, {fc.get('HIGH', 0)} high")
    for f in [f for f in r["flags"] if f["severity"] == "HIGH"][:10]:
        print(f"  ! [{f['area']}] {f['check']} ({f['year']}): expected {f['expected']}, reported {f['reported']}")
    for cat in r["categories"]:
        print(f"{cat['name']:<18} {cat['pct']:.0%}  (weight {cat['weight']:.0%})")
    print(f"OVERALL {r['overall']:.0%} -> {r['band']}")
    print(f"Saved: {a.out / r['output_file']}")


if __name__ == "__main__":
    main()
