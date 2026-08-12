"""
Segunda Mente V4.0 — FastAPI app principal (mount).
Servido pela Vercel via vercel.json (rewrites /api/(.*) -> /api/index).

IMPORTANTE: este é o ÚNICO arquivo dentro de /api (fora de _lib) que deve
existir sem ser precedido de "_". O runtime Python da Vercel trata todo
arquivo .py solto em /api como uma Serverless Function independente e
exige que ele exporte uma variável `app` (ASGI) ou `handler`. Por isso
todos os módulos de rota (capture, contents, search_route, projects, tags,
stats, process) vivem em api/_lib/routers/ — a Vercel ignora diretórios
prefixados com "_", então eles são apenas módulos Python normais,
importados e montados aqui como routers do FastAPI.
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

# Importar e incluir routers (localizados em api/_lib/routers/ — ver nota acima)
from api._lib.routers.capture import router as capture_router
from api._lib.routers.contents import router as contents_router
from api._lib.routers.search_route import router as search_router
from api._lib.routers.projects import router as projects_router
from api._lib.routers.tags import router as tags_router
from api._lib.routers.stats import router as stats_router
from api._lib.routers.process import router as process_router

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """
    Rede de segurança: qualquer exceção não tratada em uma rota vira um
    JSON com detail legível em vez de um 500 opaco — facilita depurar
    problemas de configuração (env vars ausentes, Supabase fora do ar, etc.)
    direto pelo toast do frontend.
    """
    from fastapi.responses import JSONResponse
    logging.getLogger(__name__).exception("Erro não tratado em %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": f"Erro interno: {exc}"})
