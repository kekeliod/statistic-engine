# Single image: builds the React frontend, then serves it + the API from one
# Python process. Used by container hosts (Hugging Face Spaces, Render, Railway,
# Fly.io, a VPS). Not needed for the local / shared-link workflow.

# ---- stage 1: build the frontend ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: python runtime ----
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend/dist

# Keep the database and uploaded files in /data so a host can mount a volume there.
# (The frontend is served from the same origin as the API, so no CORS config is needed.)
ENV DATABASE_URL=sqlite:////data/app.db \
    UPLOAD_DIR=/data/uploads
RUN mkdir -p /data/uploads

WORKDIR /app/backend
EXPOSE 8000
# Shell form so hosts that inject $PORT (Render, Railway) are respected.
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
