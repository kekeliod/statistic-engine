from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine
from app.models import (  # noqa: F401  (registers models on Base.metadata)
    Analysis,
    Chart,
    ChatMessage,
    Dataset,
    Project,
    Report,
)
from app.routers import analyses, charts, chat, datasets, projects, reports

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Research Data Analysis Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(analyses.router)
app.include_router(charts.router)
app.include_router(chat.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    from app.services.ai.client import ai_available

    return {"status": "ok", "ai_available": ai_available()}


# ── Serve the built frontend (single-service mode) ─────────────────────────
# When frontend/dist exists (produced by `npm run build`), the same server that
# hosts the API also serves the React app, so the whole product is one URL /
# one process — which is what the "share a link" workflow and the Docker image
# both rely on. In local dev you instead run Vite separately and this block is
# simply skipped.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _DIST.is_dir():
    if (_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # Unmatched /api/* paths are real 404s, not the SPA.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
