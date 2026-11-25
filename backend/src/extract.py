"""Step 1 – AI extraction: send both PDFs to Claude, get schema-valid JSON back."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import anthropic

from .schema import Extraction

MODEL = "claude-opus-5-5"

SYSTEM = """You are an investment analyst at AHL Venture Partners, an Africa-focused \
private-debt investor, preparing a first-pass screening (TMS) of a company.

You receive two documents: (1) an investment memo written by the company and \
(2) its audited financial statements plus a budget year. Produce the JSON object \
defined by the response schema.

Transcription rules (financials):
- Copy every number exactly as printed in the financial statements, in the \
statement's units (USD '000). Never correct, recompute or "fix" a figure, even \
when it looks wrong - a separate validation step checks arithmetic and needs \
the figures as printed.
- Bracketed numbers are negative. '—', '(—)', '(−)' or an empty cell is null.
- Percentages as decimals (34% -> 0.34).
- The memo's "Selected Financials" table goes in memo.memo_financial_table, \
also exactly as printed.

Memo rules:
- Every fact carries a short source reference ("Memo p.2 Management & Governance").
- Record what the memo claims, including claims that may be wrong (e.g. \
country tiers, capital efficiency, funding totals). Do not reconcile \
contradictions; capture each side so they can be flagged.
- If the documents are silent on something, say so - never infer facts.

Screening judgements (screen.*):
- Score each qualitative criterion 1-3 strictly against the guide below, \
using only evidence in the documents. Use null when there is no information \
(e.g. deal source not stated). Be appropriately sceptical: a claim made only \
by the company's own memo, without independent support, should not \
automatically receive the top score - say what DD must confirm.

Guide:
deal_origination: 1 cold inbound; 3 recommended by trusted source with no vested interest.
breadth: 1 single founder, first-time c-suite, key-man risk; 2 >1 founder plus SLT, some gaps; 3 mature professional team, well incentivised, clear scope of responsibilities.
in_market: 1 CEO outside market; 2 one of c-suite outside market; 3 everyone in market.
team_churn: 1 more than one SLT member joined in last 2 years; 3 all SLT there >2 years.
reputation: 1 web search shows significant reputational concern on company/founder; 2 concern on SLT; 3 no adverse results.
governance: 1 management-only board, undocumented responsibilities; 3 independent non-execs of substance, documented board charter and SLT JDs, frequent formal meetings.
stakeholders: 1 institutional shareholders with significant influence or funds at end of life / limited dry powder; 3 support by large PE fund with significant dry powder.
customer_ltv: 1 one-off purchase, little upsell/recurring revenue; 3 customers repeat for multiple years or long-term contracts.
customer_focus: 3 management describes value proposition clearly in customer terms, significant value-add vs alternatives, tracks customer satisfaction.
competitive_moat: 1 few barriers, easy to execute, fragmented market; 3 high barriers from regulation, tech, scale, partnerships, cost advantage.
new_products_markets: 1 small/low-growth market, no clear reason for share gains; 3 fast-growing market with barriers to entry.
funding_requirement: 1 capital-light / likely < $5m capital over 3 years; 3 credible plans to absorb an additional $20m of debt over 3 years.
market_size: 1 non-essential products, single country; 3 essential products, multi-country or export.
"""


def _strict_json_schema(model: type) -> dict:
    """Pydantic schema -> self-contained schema accepted by structured outputs."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(dict(defs[node["$ref"].split("/")[-1]]))
            node = {k: walk(v) for k, v in node.items() if k not in ("title", "default")}
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            return node
        if isinstance(node, list):
            return [walk(n) for n in node]
        return node

    return walk(schema)


def _pdf_block(path: Path, title: str) -> dict:
    return {
        "type": "document",
        "title": title,
        "source": {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64.standard_b64encode(path.read_bytes()).decode(),
        },
    }


def extract(memo_pdf: Path, financials_pdf: Path) -> tuple[Extraction, dict]:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # if a request is declined, the API retries on a fallback model
        system=SYSTEM,
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": _strict_json_schema(Extraction)},
        },
        messages=[{
            "role": "user",
            "content": [
                _pdf_block(memo_pdf, "Investment Memo"),
                _pdf_block(financials_pdf, "Audited Financial Statements and Budget"),
                {"type": "text", "text": "Extract and assess per the schema."},
            ],
        }],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError(f"Model declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Response truncated (max_tokens) - extraction incomplete")

    text = next(b.text for b in response.content if b.type == "text")
    data = Extraction.model_validate_json(text)  # second, local schema check
    usage = {
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return data, usage


def load(path: Path) -> Extraction:
    return Extraction.model_validate(json.loads(path.read_text()))
