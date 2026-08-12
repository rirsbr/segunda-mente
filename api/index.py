import sys
import os
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("segunda_mente")

app = FastAPI(title="Segunda Mente V4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug: catch-all para ver que path o Vercel envia
@app.api_route("/debug-path", methods=["GET"])
@app.api_route("/api/debug-path", methods=["GET"])
async def debug_path(request: Request):
    return {
        "path": request.url.path,
        "query": str(request.query_params),
        "base_url": str(request.base_url),
        "url": str(request.url),
        "scope_path": request.scope.get("path", "N/A"),
        "root_path": request.scope.get("root_path", "N/A"),
    }

# Health em ambos os paths possíveis
@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0"}

# Catch-all no final
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
async def catch_all(request: Request, full_path: str):
    return {
        "caught": True,
        "full_path": full_path,
        "request_path": request.url.path,
        "method": request.method
    }
