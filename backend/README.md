# TMS Screening Automation

Turns an investment memo and financial statements (PDF) into a completed AHL TMS screening template (Excel). The output records where each value came from and flags inconsistencies in the source documents.

```
 Memo.pdf ─┐                                ┌─> 2 VALIDATE (rules)    112 checks: arithmetic, roll-forwards,
           ├─> 1 EXTRACT (Claude) ─> JSON ──┤                           memo vs FS, memo claims vs AHL data
 FS.pdf ───┘   schema-checked output        ├─> 3 SCORE (rules)       quantitative TMS criteria
                                            └─> 4 POPULATE (YAML map) template + Extraction Log,
                                                                      Validation Flags, Automation Notes
```

**Design principle:** the AI only reads and judges. Arithmetic, sign conventions, ratios and quantitative scores are done by deterministic code, so every number can be re-derived.

| Step | File | What it does |
|---|---|---|
| 1 | `src/extract.py`, `src/schema.py` | Sends both PDFs to Claude (`claude-opus-5-5`). Structured output guarantees the JSON matches the schema. Figures are transcribed exactly as printed. Every memo fact carries a source reference. 13 judgement criteria are scored against the TMS guide. |
| 2 | `src/validate.py` | Recomputes subtotals. Ties the P&L, balance sheet and cash flow together. Compares the memo table with the statements, country tiers with the Gating Screen, and recomputes the claimed ratios. |
| 3 | `src/score.py` | Scores revenue growth, profitability, unit profitability, capital efficiency and use of leverage using the template's own thresholds. |
| 4 | `src/populate.py`, `config/field_map.yaml` | Writes the cells. **To change the cell mapping, edit only the YAML file.** Also fixes known template bugs and adds three audit sheets. |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python run.py                                      # live run (about 1-2 minutes)
.venv/bin/python tests/compare_to_reference.py output/extraction.json   # accuracy vs hand-checked reference
.venv/bin/python run.py --replay output/extraction.json      # re-run steps 2-4 with no API call
```

Defaults point to the case-study files in the parent folder. Use `--memo`, `--financials` and `--template` to process another company.

## Outputs (`output/`)
- `<Company>_TMS_Screening.xlsx`: completed template. Excel recalculates all formulas when the file is opened.
- `extraction.json`: the raw AI extraction, which can be audited or replayed.
- `validation_flags.json`: all checks with their severity.

`tests/agriwave_reference_extraction.json` is a hand-checked transcription of the AgriWave documents. It is used to test steps 2–4 offline and to measure the accuracy of the live extraction.
