# ── IntentGuard Purple Agent ──────────────────────────────────────────────────
# Containerises the existing IntentGuard Python codebase as an AgentBeats
# Purple Agent.  Build with:
#   docker build -t intentguard-purple .
# Run locally with:
#   docker run --env-file .env -p 8000:8000 intentguard-purple

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── install Python dependencies first (layer cache) ──────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn[standard] python-dotenv

# ── copy application code ─────────────────────────────────────────────────────
COPY cli.py              ./cli.py
COPY smart_home_agent.py ./smart_home_agent.py
COPY ingestdata.py      ./ingestdata.py
COPY a2a_handler.py      ./a2a_handler.py

# Copy data files that are already generated / committed to the repo
COPY smartthings_data.txt  ./smartthings_data.txt
COPY generated_rules.json  ./generated_rules.json

# ── runtime ───────────────────────────────────────────────────────────────────
# API keys are injected at runtime via --env-file or -e flags (never baked in)
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "a2a_handler:app", "--host", "0.0.0.0", "--port", "8000"]