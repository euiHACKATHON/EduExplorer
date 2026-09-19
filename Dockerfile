FROM python:3.11-slim

WORKDIR /app

# build-essential covers any dependency that needs a C extension compiled
# (some transitive deps under langgraph/groq do); slim base keeps the image
# small otherwise.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install from the lock file for a reproducible build. If you add a new
# top-level dependency: add it to requirements.txt, run
# `pip freeze > requirements-lock.txt` locally, commit both.
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# $PORT is set by most PaaS platforms (Render, Railway) at runtime and
# overrides the 8000 default; shell form so the env var actually expands.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
