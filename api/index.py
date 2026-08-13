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

# Middleware que corrige o path real da request.
# O Vercel rewrite manda tudo para /api/index?_path=<path_real>
# Este middleware restaura o path original antes do FastAPI rotear.
@app.middleware("http")
async def fix_vercel_path(request: Request, call_next):
    real_path = request.query_params.get("_path")
    if real_path:
        # Reconstroi o path original
        if not real_path.startswith("/"):
            real_path = "/" + real_path
        if not real_path.startswith("/api"):
            real_path = "/api" + real_path
        request.scope["path"] = real_path
        # Remove _path dos query params para não poluir
        q = str(request.query_params)
        params = {k: v for k, v in request.query_params.items() if k != "_path"}
        if params:
            request.scope["query_string"] = "&".join(f"{k}={v}" for k, v in params.items()).encode()
        else:
            request.scope["query_string"] = b""
    return await call_next(request)

# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0", "routers_loaded": sorted(_loaded_routers)}

# Exception handler
@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Erro em %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": f"Erro interno: {exc}"})

# Importar routers
_loaded_routers: set = set()
_ROUTER_MODULES = [
    ("capture", "api._lib.routers.capture"),
    ("contents", "api._lib.routers.contents"),
    ("search_route", "api._lib.routers.search_route"),
    ("projects", "api._lib.routers.projects"),
    ("tags", "api._lib.routers.tags"),
    ("stats", "api._lib.routers.stats"),
    ("process", "api._lib.routers.process"),
    ("reclassify", "api._lib.routers.reclassify"),
    ("generate_prompt", "api._lib.routers.generate_prompt"),
]

for _name, _module_path in _ROUTER_MODULES:
    try:
        _module = __import__(_module_path, fromlist=["router"])
        app.include_router(_module.router, prefix="/api")
        _loaded_routers.add(_name)
        logger.info("Router '%s' carregado.", _name)
    except Exception as exc:
        logger.error("ERRO router '%s': %s", _name, exc)
        traceback.print_exc()

# Debug route
@app.get("/api/_debug/routers")
async def debug_routers():
    all_names = [name for name, _ in _ROUTER_MODULES]
    return {
        "loaded": sorted(_loaded_routers),
        "failed": sorted(set(all_names) - _loaded_routers),
        "routes": sorted({getattr(r, "path", str(r)) for r in app.routes}),
    }
