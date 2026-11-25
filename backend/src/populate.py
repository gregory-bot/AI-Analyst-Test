"""Step 4 – write extracted, validated and scored data into the TMS template."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import openpyxl
import yaml
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .schema import Extraction
from .score import Score
from .validate import Flag

AUTHOR = "TMS automation"
WRAP = Alignment(wrap_text=True, vertical="top")
HDR = Font(bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor="2E2A5E")
SEV_FILL = {"HIGH": "F8CBAD", "MEDIUM": "FFE699", "INFO": "E2EFDA"}


def _note(cell, text):
    cell.comment = Comment(text, AUTHOR, width=320, height=110)


def _field(x: Extraction, path: str):
    obj = x.financials
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def gating_table(template: Path) -> dict[str, str]:
    from .validate import _norm
    ws = openpyxl.load_workbook(template, read_only=True)["Country Gating Screen"]
    return {_norm(r[0]): r[1] for r in ws.iter_rows(min_row=9, max_row=62, min_col=3, max_col=4, values_only=True) if r[0]}


def populate(template: Path, out: Path, x: Extraction, flags: list[Flag], rule_scores: list[Score],
             ahl_debt_usd: float, cfg_path: Path, run_meta: dict) -> list[str]:
    cfg = yaml.safe_load(cfg_path.read_text())
    wb = openpyxl.load_workbook(template)
    fo, tms, cur = wb["Financial Overview"], wb["TMS Assessment"], wb["Currency Data"]
    log: list[tuple] = []          # Extraction Log rows
    fixes: list[str] = []          # template fixes applied

    # ------------------------------------------------------------------ #
    # 0. Template fixes (documented in the Automation Notes sheet)        #
    # ------------------------------------------------------------------ #
    cur["F16"], cur["F34"] = 1, 1
    for col in "CDEF":
        for row, rng in ((93, ("$C$22:$E$35", "$C$21:$E$21")), (94, ("$C$4:$E$17", "$C$3:$E$3"))):
            c = fo[f"{col}{row}"]
            c.value = c.value.replace(rng[0], rng[0].replace("$E$", "$F$")).replace(rng[1], rng[1].replace("$E$", "$F$"))
    fixes.append("Currency Data: added 2025 USD rate (=1) and extended FX lookups (rows 93-94) to include 2025 - "
                 "previously returned #N/A, zeroing every USD-converted figure in columns I-L.")
    fo["F7"] = '=IFERROR(F6/E6-1,"n/a")'
    fixes.append("Financial Overview F7: revenue growth formula compared to D6 (two years back); corrected to E6.")
    for col, src in zip("IJKL", "CDEF"):
        fo[f"{col}28"] = f"={src}5"
    fixes.append("Financial Overview I28:L28: replaced hard-coded 2022-2024 dates left over from a prior deal with year links.")
    fixes.append("Financial Overview C23: stray '`' character overwritten by tax input.")
    fixes.append("User Guide refers to a 'Product Screen' tab that is not in the template: proposed structure and key DD "
                 "areas are written to the 'Automation Notes' sheet instead.")

    # ------------------------------------------------------------------ #
    # 1. Financial Overview                                               #
    # ------------------------------------------------------------------ #
    mult = cfg["units_multiplier"]
    fo["B5"] = cfg["currency"]
    for col, yc in cfg["year_columns"].items():
        fo[f"{col}5"] = yc["label"]
        fo[f"{col}66"] = yc["label"]
    _note(fo["F5"], "FY2025 = company budget/forecast (unaudited).")

    for row, spec in cfg["financial_overview"].items():
        for col, yc in cfg["year_columns"].items():
            total, parts = 0.0, []
            for path in spec["fields"]:
                val = getattr(_field(x, path), yc["source"])
                total += val or 0.0
                parts.append(f"{path.split('.')[-1]}={val}")
            if spec.get("negate"):
                total = -total
            fo[f"{col}{row}"] = round(total * mult, 2)
            log.append(("Financial Overview", f"{fo[f'B{row}'].value} {yc['label']}", total * mult,
                        "FS: " + ", ".join(parts) if parts else "n/a - none disclosed", f"Financial Overview!{col}{row}"))
        if spec.get("note"):
            _note(fo[f"C{row}"], spec["note"])

    fo["L99"] = ahl_debt_usd
    _note(fo["L99"], "AHL ask = senior secured debt tranche from the memo's use of proceeds.")

    # ------------------------------------------------------------------ #
    # 2. TMS Assessment - header                                          #
    # ------------------------------------------------------------------ #
    m, s = x.memo, x.screen
    uop = "; ".join(f"${u.usd/1e6:.0f}m {u.instrument.replace('_', ' ')} - {u.purpose}" for u in m.use_of_proceeds)
    debt_ask = sum(u.usd for u in m.use_of_proceeds if u.instrument == "senior_secured_debt")
    from .validate import _norm
    gating = gating_table(template)
    tiers = ", ".join(f"{c} {gating.get(_norm(c), 'not listed')}" for c in m.operating_countries + m.planned_countries)
    wrong = "; ".join(f"{c.country} as {c.tier_claimed_in_memo}" for c in m.country_tier_claims
                      if gating.get(_norm(c.country), c.tier_claimed_in_memo).lower() != c.tier_claimed_in_memo.lower())
    header = {
        2: ("No management call yet - to be completed by deal lead.", None),
        3: (m.business_description.value, None),
        5: (m.company_name.value, None),
        6: (m.sector.value, None),
        7: ("Senior secured debt - revolving/seasonal loan-book facility", "Matches AHL private-debt product; use of proceeds is loan-book expansion."),
        8: (debt_ask, f"Total raise ${m.funding_total_use_of_proceeds.usd/1e6:.0f}m: {uop}. "
                      f"Memo intro says '${m.funding_headline.usd/1e6:.0f}m in {m.funding_headline_instrument_wording.value}' - "
                      "inconsistent with use of proceeds; AHL ask taken as the debt tranche."),
        9: (s.impact_toc, s.impact_rationale),
        10: (s.climate_alignment, s.climate_rationale),
        11: (s.two_x_alignment, s.two_x_rationale),
        12: (m.primary_country, f"Operating: {', '.join(m.operating_countries)}. Planned: {', '.join(m.planned_countries)}. "
                                f"AHL Country Gating Screen: {tiers}." + (f" Memo misstates: {wrong}." if wrong else "")),
        13: (s.local_founder, s.local_founder_rationale),
        15: (s.security_workable, f"{m.security_package.value} {m.collateral_liquidation.value} {s.security_rationale}"),
    }
    for row, (val, comment) in header.items():
        tms[f"B{row}"] = val
        tms[f"B{row}"].alignment = WRAP
        if comment:
            tms[f"C{row}"] = comment
            tms[f"C{row}"].alignment = WRAP
        log.append(("TMS Assessment", tms[f"A{row}"].value, val, comment or "", f"TMS Assessment!B{row}"))
    tms["B8"].number_format = '"$"#,##0'
    tms["B4"] = None
    tms["C4"] = "Requires AHL portfolio list (not in source documents) - deal lead to select None/Low/Medium/High."

    # ------------------------------------------------------------------ #
    # 3. TMS Assessment - risk matrix                                     #
    # ------------------------------------------------------------------ #
    rows = cfg["risk_matrix_rows"]
    all_scores = [(q.criterion, q.score, q.rationale, q.evidence, "AI judgement", q.dd_question) for q in s.qualitative_scores]
    all_scores += [(r.criterion, r.score, r.rationale, r.evidence, "Rule-based", "") for r in rule_scores]
    for crit, score, rationale, evidence, method, dd in all_scores:
        row = rows[crit]
        tms[f"D{row}"] = score
        text = f"[{method}] {rationale} (Source: {evidence})" + (f" DD: {dd}" if dd else "")
        tms[f"E{row}"] = text
        tms[f"E{row}"].alignment = WRAP
        log.append(("TMS Risk Matrix", tms[f"A{row}"].value, score, text, f"TMS Assessment!D{row}"))

    # ------------------------------------------------------------------ #
    # 4. Data validations openpyxl cannot round-trip (x14 extension)      #
    # ------------------------------------------------------------------ #
    for ws, ref, formula in ((fo, "B5", "'Currency Data'!$B$4:$B$17"),
                             (tms, "B12", "'Country Gating Screen'!$C$9:$C$62")):
        dv = DataValidation(type="list", formula1=formula, allow_blank=True)
        dv.add(ref)
        ws.add_data_validation(dv)

    # ------------------------------------------------------------------ #
    # 5. Audit-trail sheets                                               #
    # ------------------------------------------------------------------ #
    _sheet(wb, "Validation Flags", ["Severity", "Area", "Check", "Year", "Expected / recomputed", "Reported", "Note"],
           [(f.severity, f.area, f.check, f.year, f.expected, f.reported, f.note)
            for f in sorted(flags, key=lambda f: {"HIGH": 0, "MEDIUM": 1, "INFO": 2}[f.severity])],
           widths=[10, 16, 50, 8, 30, 22, 80], sev_col=0)
    _sheet(wb, "Extraction Log", ["Sheet", "Field", "Value written", "Source / rationale", "Cell"],
           log, widths=[18, 40, 22, 100, 26])

    notes = [("Run", f"{run_meta['timestamp']} | mode: {run_meta['mode']} | model: {run_meta.get('model', '-')}"),
             ("Inputs", run_meta["inputs"]),
             ("Proposed structure",
              f"${debt_ask/1e6:.0f}m senior secured facility for seasonal loan-book expansion; ~9-12 month revolving "
              "drawdowns matched to crop cycle; security: pledge over loan receivables and produce inventory "
              "(+ assignment of processor offtake contracts). Covenants to test: borrowing base (eligible "
              "receivables / facility), PAR30, D:E <= 3x. Equity ($4m) to be led by another investor."),
             ]
    notes += [(f"Key DD area {i}", d) for i, d in enumerate(s.key_dd_areas, 1)]
    notes += [(f"Template fix {i}", t) for i, t in enumerate(fixes, 1)]
    notes += [("Legend", "Yellow input cells populated by automation. Cell notes explain mappings. Every value is "
                         "traceable in 'Extraction Log'; arithmetic checks are in 'Validation Flags'.")]
    _sheet(wb, "Automation Notes", ["Item", "Detail"], notes, widths=[22, 140])

    wb.calculation.fullCalcOnLoad = True  # Excel recalculates all formulas on open
    wb.active = wb.sheetnames.index("TMS Assessment")
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return fixes


def _sheet(wb, name, headers, rows, widths, sev_col=None):
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = HDR, HDR_FILL
    for r in rows:
        ws.append(list(r))
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP
        if sev_col is not None:
            row[sev_col].fill = PatternFill("solid", fgColor=SEV_FILL.get(row[sev_col].value, "FFFFFF"))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
