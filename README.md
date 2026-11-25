# AI Analyst Case Study: TMS Screening Automation

This tool automates the first-pass screening of an investment opportunity. You upload a company's **investment memo** and **financial statements**. The tool returns a completed **TMS screening template** (Excel), a validation report on the source documents, and a source reference for every value it wrote.

Built for the AHL Venture Partners AI Analyst technical case study (sample company: AgriWave Ltd).

```
AI Analyst Test/
├── README.md                     ← you are here
├── AHL Automation Technical Case Study.pdf          ┐
├── AgriWave Ltd Investment Memo.pdf                 │ case-study documents
├── AgriWave Ltd Audited Financial Statements…pdf    │ (also used as sample inputs)
├── 2025.12_Screening Template vF.xlsx               ┘
├── backend/                      Python · FastAPI · OpenAI API
│   ├── .env                      OPENAI_API_KEY lives here (git-ignored)
│   ├── api.py                    REST API used by the frontend
│   ├── run.py                    same pipeline from the command line
│   ├── src/                      extract → validate → score → populate
│   ├── config/field_map.yaml     template cell map (edit this, not code, if the template changes)
│   └── tests/                    hand-checked reference extraction + accuracy checker
└── frontend/                     React (Vite) web app
    └── src/                      upload → progress → results screens
```

## How it works

| Step | Engine | What happens |
|---|---|---|
| 1. Extract | **OpenAI** (`gpt-5.5`, configurable) | Reads both PDFs via the Responses API and returns JSON in a strict schema (Structured Outputs from the Pydantic model). It copies figures exactly as printed, gives a source for each memo fact, and scores the 13 judgement criteria against the TMS guide. |
| 2. Validate | Rules (Python) | 112 checks: subtotals, links between the P&L, balance sheet and cash flow, the memo's financial table against the statements, the memo's claims against AHL's Country Gating Screen, and the plausibility of the loan-book yield. |
| 3. Score | Rules (Python) | Scores revenue growth, profitability, unit profitability, capital efficiency and use of leverage using the template's own thresholds. |
| 4. Populate | openpyxl + YAML map | Fills the template, fixes 5 template bugs, and adds *Extraction Log*, *Validation Flags* and *Automation Notes* sheets. |

The AI only reads documents and makes judgements. All arithmetic is done by deterministic code, so every number can be traced and re-derived.

## Quick start

**Requirements:** Python 3.10 or later, Node 18 or later, and an OpenAI API key (optional; without one, only demo mode works). Create one at https://platform.openai.com/api-keys and add billing credit at https://platform.openai.com/settings/organization/billing.

### 1. Backend (port 8000)
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# put your key in backend/.env →  OPENAI_API_KEY=sk-...
.venv/bin/uvicorn api:app --port 8000
```

### 2. Frontend (port 5173)
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**, upload the memo and financials (or tick *Use the sample AgriWave documents*), and click **Run screening**.

**Live** mode calls OpenAI and takes about 1–2 minutes. **Demo** mode replays a saved, hand-checked AgriWave extraction, so it needs no API key and finishes in seconds. Steps 2–4 run in full in both modes.

### Command line (no frontend)
```bash
cd backend
.venv/bin/python run.py            # live, uses the sample documents in the root folder
.venv/bin/python run.py --demo     # no API key needed
.venv/bin/python tests/compare_to_reference.py output/extraction.json   # accuracy vs reference
```

## Configuration

| File | Variable | Purpose |
|---|---|---|
| `backend/.env` | `OPENAI_API_KEY` | OpenAI API key (required for live mode) |
| `backend/.env` | `OPENAI_MODEL` | Extraction model, default `gpt-5.5` (needs PDF input + structured outputs) |
| `backend/.env` | `OPENAI_REASONING_EFFORT` | `low` / `medium` / `high` for reasoning models (default `medium`) |
| `backend/.env` | `ALLOWED_ORIGINS` | Origins allowed to call the API (default `http://localhost:5173`) |
| `frontend/.env` | `BACKEND_URL` | Where the dev server proxies `/api` (default `http://127.0.0.1:8000`) |
| `frontend/.env` | `VITE_API_URL` | Optional: call a deployed backend directly |

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Backend status, whether the API key is configured, whether sample documents are present |
| `POST` | `/api/jobs` | multipart: `memo` (pdf), `financials` (pdf), `template` (xlsx, optional), `mode` = `live`\|`demo`, `use_samples` |
| `GET` | `/api/jobs/{id}` | Poll status, current step and (when finished) the full results |
| `GET` | `/api/jobs/{id}/download` | Download the completed TMS Excel file |

## Deploying the backend to Render

`render.yaml` in the repo root is a Render Blueprint for the API.

1. Push the repo to GitHub. Then, in Render: **New → Blueprint**, select the repo, and click **Apply**.
2. When prompted, set the two secret variables:
   - `OPENAI_API_KEY`: your OpenAI key
   - `ALLOWED_ORIGINS`: the frontend URL(s), comma-separated (e.g. `https://your-app.netlify.app,http://localhost:5173`)
3. Wait for the deploy to finish, then open `https://<service>.onrender.com/api/health`. It should return `"api_key_configured": true`.
4. Point the frontend at the API by setting `VITE_API_URL=https://<service>.onrender.com` (in `frontend/.env` locally, or in your Netlify/Vercel environment variables) and rebuild.

Render runs `pip install -r backend/requirements.txt` and then `cd backend && uvicorn api:app --host 0.0.0.0 --port $PORT` on Python 3.12. On the free plan the service sleeps after 15 minutes idle, so the first request takes about 50 seconds to wake it. Jobs and generated files live in memory and on temporary disk, so they are lost when the service restarts.

## Outputs
- **Completed TMS template**: Financial Overview and TMS Assessment filled in. Excel recalculates every formula when the file is opened.
- **Extraction Log** sheet: every value written, with its source and the cell it went to.
- **Validation Flags** sheet: every check, ranked by severity.
- **Automation Notes** sheet: proposed structure, key DD areas, template fixes and run details.

## Limitations and assumptions
- The template has 4 year columns: FY2022–FY2024 are audited, and FY2025 is the company's budget. FY2021 is used only for the 3-year growth test.
- Figures are entered as reported. Where the documents contradict themselves, the template uses the line items and the gap is flagged, not silently fixed.
- Judgement scores rely only on the documents. Items that need a management call or the AHL portfolio list (deal source, competition with portfolio) are left blank for the deal lead.
- Jobs are held in memory on the backend. This is fine for a demo; a production version would need a database and authentication.
