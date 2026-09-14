"""
DataLens AI — Backend
A FastAPI server that accepts raw/CSV data pasted by the user, sends it to the
Anthropic Claude API, and streams back a plain-language explanation of the
data (trends, outliers, summary stats, suggested next steps).

Security notes:
- The Anthropic API key lives only in the environment (.env / AWS env vars),
  never in frontend code or version control.
- CORS is restricted via an env var so only your deployed frontend origin
  can call this API in production.
"""

import os
import json
import csv
import io
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# LLM provider config. Defaults to NVIDIA NIM's free, OpenAI-compatible
# endpoint. To use Anthropic or OpenAI directly instead, change LLM_BASE_URL
# and LLM_API_KEY / MODEL_NAME accordingly (e.g. base_url=None + Anthropic SDK).
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("NVIDIA_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "meta/llama-3.1-70b-instruct")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

if not LLM_API_KEY:
    # Fail loudly at startup rather than silently at request time.
    print("WARNING: LLM_API_KEY is not set. Set it in your .env file.")

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

app = FastAPI(title="DataLens AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    data_text: str          # raw pasted CSV or free-form data
    question: str = ""      # optional user question, e.g. "any seasonality?"


MAX_CHARS = 80000  # guard against oversized payloads


def sniff_and_summarize(data_text: str) -> tuple[str, int]:
    """
    Returns (sample_text_for_model, actual_total_row_count).
    Row count is computed from the FULL input, not the truncated sample.
    """
    full_stripped = data_text.strip()
    try:
        full_reader = csv.reader(io.StringIO(full_stripped))
        all_rows = list(full_reader)
        total_rows = max(len(all_rows) - 1, 0)  # minus header
        headers = all_rows[0] if all_rows else []
    except Exception:
        total_rows = 0
        headers = []

    sample = full_stripped[:MAX_CHARS]
    if headers:
        return (
            f"[Dataset: {len(headers)} columns "
            f"({', '.join(headers[:10])}{'...' if len(headers) > 10 else ''}), "
            f"{total_rows} TOTAL rows. You are being shown a SAMPLE of the "
            f"first rows below due to size limits — do not state row counts "
            f"as if this sample were the whole dataset; always use the "
            f"TOTAL figure given here.]\n\n{sample}",
            total_rows,
        )
    return (sample, total_rows)


SYSTEM_PROMPT = (
    "You are DataLens AI, a senior data analyst. You are given a dataset "
    "(full or sampled) and must produce a clear, plain-language analysis "
    "for a non-technical audience. Always use the TOTAL row count given to "
    "you, never the number of rows you can literally see if you're working "
    "from a sample.\n\n"
    "Structure your response as:\n"
    "1) **Summary** — what the dataset contains, its scale, and scope.\n"
    "2) **Key patterns** — 3-5 real trends, correlations, or relationships "
    "between columns (e.g. 'higher discount % correlates with lower review "
    "ratings'). Prefer relationships between 2+ columns over single-column "
    "observations.\n"
    "3) **Outliers & data quality** — anything that looks unusual, "
    "inconsistent, or worth double-checking (missing values, extreme "
    "values, duplicate-looking rows).\n"
    "4) **Notable segments** — if there are natural groupings (by category, "
    "location, time period, etc.), call out which segments over- or "
    "under-perform relative to the rest.\n"
    "5) **Suggested next steps** — 1-2 concrete follow-up analyses someone "
    "could run.\n\n"
    "If the user asks a specific or scenario-based question (e.g. 'what "
    "would happen if we removed the top 10% of spenders?', 'which segment "
    "should we target next?'), answer that question directly and "
    "quantitatively using the data shown, reasoning step by step from the "
    "actual numbers rather than giving generic advice. State clearly when "
    "you're estimating or extrapolating due to only seeing a sample.\n\n"
    "Be concise, avoid jargon unless briefly explained, and if the input "
    "doesn't look like real data, say so plainly and ask for clarification."
)


async def stream_claude_response(data_text: str, question: str) -> AsyncGenerator[str, None]:
    prepared, total_rows = sniff_and_summarize(data_text)
    user_content = prepared
    if question.strip():
        user_content += f"\n\nSpecific question from the user: {question.strip()}"
    

    try:
        stream = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                # Server-Sent-Events style chunks the frontend can read progressively
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.data_text or not req.data_text.strip():
        raise HTTPException(status_code=400, detail="data_text must not be empty")
    if not LLM_API_KEY:
        raise HTTPException(status_code=500, detail="Server is missing LLM_API_KEY")

    return StreamingResponse(
        stream_claude_response(req.data_text, req.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering for real streaming
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME}


# Serve the built frontend (index.html, css, js) as static files in production.
# The Dockerfile copies frontend/ into /app/static.
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
