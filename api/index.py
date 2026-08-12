"""
Segunda Mente V4.0 — FastAPI app principal (mount).
Servido pela Vercel via vercel.json (rewrites /api/(.*) -> /api/index).
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Segunda Mente V4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar e incluir routers
from api.capture import router as capture_router
from api.contents import router as contents_router
from api.search_route import router as search_router
from api.projects import router as projects_router
from api.tags import router as tags_router
from api.stats import router as stats_router
from api.process import router as process_router

app.include_router(capture_router, prefix="/api")
app.include_router(contents_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(process_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0"}
