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
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL_NAME = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

if not ANTHROPIC_API_KEY:
    # Fail loudly at startup rather than silently at request time.
    print("WARNING: ANTHROPIC_API_KEY is not set. Set it in your .env file.")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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


MAX_CHARS = 20000  # guard against oversized payloads


def sniff_and_summarize(data_text: str) -> str:
    """
    Give the model a lightweight structural hint (columns, row count) when the
    input looks like CSV, so it doesn't have to guess the schema from scratch.
    Falls back gracefully for free-form text.
    """
    sample = data_text.strip()[:MAX_CHARS]
    try:
        reader = csv.reader(io.StringIO(sample))
        rows = list(reader)
        if len(rows) >= 2 and len(rows[0]) > 1:
            headers = rows[0]
            return (
                f"[Detected CSV-like input: {len(headers)} columns "
                f"({', '.join(headers[:10])}{'...' if len(headers) > 10 else ''}), "
                f"~{len(rows) - 1} data rows]\n\n{sample}"
            )
    except Exception:
        pass
    return sample


SYSTEM_PROMPT = (
    "You are DataLens AI, a data analyst assistant. You are given raw pasted "
    "data (often CSV) and must explain it in clear, plain language for a "
    "non-technical audience. Structure your response with: 1) a short "
    "summary of what the dataset appears to contain, 2) 3-5 key insights or "
    "patterns, 3) any notable outliers or data quality issues, 4) one or two "
    "suggested next steps for analysis. Be concise, use everyday language, "
    "and avoid jargon unless you briefly explain it. If the input is not "
    "data-like, say so plainly and ask for clarification."
)


async def stream_claude_response(data_text: str, question: str) -> AsyncGenerator[str, None]:
    prepared = sniff_and_summarize(data_text)
    user_content = prepared
    if question.strip():
        user_content += f"\n\nSpecific question from the user: {question.strip()}"

    try:
        with client.messages.stream(
            model=MODEL_NAME,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            for text in stream.text_stream:
                # Server-Sent-Events style chunks the frontend can read progressively
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    except anthropic.APIError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.data_text or not req.data_text.strip():
        raise HTTPException(status_code=400, detail="data_text must not be empty")
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Server is missing ANTHROPIC_API_KEY")

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
