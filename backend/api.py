"""Web API for the TMS screening pipeline.

    uvicorn api:app --reload --port 8000

POST /api/jobs               upload memo + financials (+ optional template) -> job id
GET  /api/jobs/{id}          poll status, current step and (when done) the results
GET  /api/jobs/{id}/download completed TMS Excel file
GET  /api/health             is the API key configured, are sample documents present
"""
from __future__ import annotations

import os
import shutil
import threading
import traceback
import uuid

import openai
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

BACKEND = Path(__file__).resolve().parent
load_dotenv(BACKEND / ".env")

from src.extract import MODEL  # noqa: E402  (after .env is loaded)
from src.pipeline import REFERENCE, STEPS, run_pipeline  # noqa: E402

DOCS = BACKEND.parent
SAMPLES = {
    "memo": DOCS / "AgriWave Ltd Investment Memo.pdf",
    "financials": DOCS / "AgriWave Ltd Audited Financial Statements and 2025 budget.pdf",
    "template": DOCS / "2025.12_Screening Template vF.xlsx",
}
RUNS = BACKEND / "runs"
MAX_BYTES = 25 * 1024 * 1024

app = FastAPI(title="AHL TMS Screening API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")],
    allow_methods=["*"], allow_headers=["*"],
)
JOBS: dict[str, dict] = {}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": MODEL,
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "samples_available": all(p.exists() for p in SAMPLES.values()),
        "steps": STEPS,
    }


async def _save(upload: UploadFile | None, dest: Path, suffixes: tuple[str, ...], label: str) -> Path | None:
    if upload is None or not upload.filename:
        return None
    if not upload.filename.lower().endswith(suffixes):
        raise HTTPException(400, f"{label} must be a {' or '.join(suffixes)} file")
    data = await upload.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(400, f"{label} is larger than 25 MB")
    dest.write_bytes(data)
    return dest


@app.post("/api/jobs")
async def create_job(
    mode: str = Form("live"),                       # live | demo
    use_samples: bool = Form(False),
    memo: UploadFile | None = File(None),
    financials: UploadFile | None = File(None),
    template: UploadFile | None = File(None),
):
    if mode not in ("live", "demo"):
        raise HTTPException(400, "mode must be 'live' or 'demo'")
    if mode == "live" and not os.getenv("OPENAI_API_KEY", "").strip():
        raise HTTPException(400, "OPENAI_API_KEY is not set in backend/.env - add it or use demo mode")

    job_id = uuid.uuid4().hex[:12]
    inp = RUNS / job_id / "inputs"
    inp.mkdir(parents=True)
    try:
        paths = {
            "memo": await _save(memo, inp / "memo.pdf", (".pdf",), "Investment memo"),
            "financials": await _save(financials, inp / "financials.pdf", (".pdf",), "Financial statements"),
            "template": await _save(template, inp / "template.xlsx", (".xlsx",), "Screening template"),
        }
    except HTTPException:
        shutil.rmtree(RUNS / job_id, ignore_errors=True)
        raise
    for key, p in paths.items():
        if p is None:
            if use_samples or key == "template":
                paths[key] = SAMPLES[key]
            else:
                shutil.rmtree(RUNS / job_id, ignore_errors=True)
                raise HTTPException(400, f"Please upload the {key.replace('financials', 'financial statements')} PDF")

    JOBS[job_id] = {"id": job_id, "status": "queued", "step": 0, "message": "Queued", "mode": mode,
                    "files": {k: (v.name if v.parent == inp else f"{v.name} (sample)") for k, v in paths.items()},
                    "result": None, "error": None}
    threading.Thread(target=_work, args=(job_id, paths, mode), daemon=True).start()
    return {"job_id": job_id}


def _work(job_id: str, paths: dict, mode: str):
    job = JOBS[job_id]

    def on_step(i, msg):
        job.update(status="running", step=i, message=msg)

    try:
        job["result"] = run_pipeline(paths["memo"], paths["financials"], paths["template"],
                                     RUNS / job_id / "output", replay=REFERENCE if mode == "demo" else None,
                                     on_step=on_step)
        job.update(status="done", step=len(STEPS), message="Complete")
    except openai.AuthenticationError:
        job.update(status="error", error="OpenAI rejected the API key - check OPENAI_API_KEY in backend/.env.")
    except openai.RateLimitError as e:
        msg = ("Your OpenAI account has no credit - add billing at platform.openai.com/settings/organization/billing, "
               "or use demo mode." if "credit" in str(e).lower() or "quota" in str(e).lower()
               else "OpenAI rate limit reached - wait a minute and try again.")
        job.update(status="error", error=msg)
    except Exception as e:  # surface the reason to the UI, keep the trace in the server log
        traceback.print_exc()
        job.update(status="error", error=f"{type(e).__name__}: {e}")


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    return JOBS[job_id]


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job["status"] != "done":
        raise HTTPException(404, "Result not ready")
    path = RUNS / job_id / "output" / job["result"]["output_file"]
    return FileResponse(path, filename=path.name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
