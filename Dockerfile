# DataLens AI — single-container build (FastAPI backend serves the static frontend)
FROM python:3.11-slim

WORKDIR /app

# Install backend dependencies first (better Docker layer caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy the frontend into the location main.py serves as static files
COPY frontend/ ./static/

# App Runner / most AWS services expect the container to listen on 8080
ENV PORT=8080
EXPOSE 8080

# Never bake secrets into the image — ANTHROPIC_API_KEY is injected at runtime
# via AWS App Runner environment variables (or docker run -e / --env-file).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
