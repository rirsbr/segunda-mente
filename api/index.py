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
import traceback

from fastapi import FastAPI
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


# ===================================
# HEALTH CHECK — definido ANTES de qualquer import de router, de propósito.
# Se algum router falhar ao importar (dependência ausente, erro de sintaxe
# num módulo transitivo etc.), essa rota continua de pé e responde 200,
# o que já isola se o problema é "o app nem sobe" vs. "um router específico
# quebrou".
# ===================================
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0", "routers_loaded": sorted(_loaded_routers)}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """
    Rede de segurança: qualquer exceção não tratada em uma rota vira um
    JSON com detail legível em vez de um 500 opaco — facilita depurar
    problemas de configuração (env vars ausentes, Supabase fora do ar, etc.)
    direto pelo toast do frontend.
    """
    logger.exception("Erro não tratado em %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": f"Erro interno: {exc}"})


# ===================================
# ROUTERS — cada um é importado e montado isoladamente. Se um módulo
# específico falhar ao importar (ex: dependência pesada que não instalou
# no build da Vercel), os DEMAIS routers continuam funcionando e o erro
# fica registrado nos logs da função (Vercel > Deployments > Functions >
# Logs) em vez de derrubar o app inteiro silenciosamente.
# ===================================
_loaded_routers: set[str] = set()

_ROUTER_MODULES = [
    ("capture", "api._lib.routers.capture"),
    ("contents", "api._lib.routers.contents"),
    ("search_route", "api._lib.routers.search_route"),
    ("projects", "api._lib.routers.projects"),
    ("tags", "api._lib.routers.tags"),
    ("stats", "api._lib.routers.stats"),
    ("process", "api._lib.routers.process"),
]

for _name, _module_path in _ROUTER_MODULES:
    try:
        _module = __import__(_module_path, fromlist=["router"])
        app.include_router(_module.router, prefix="/api")
        _loaded_routers.add(_name)
        logger.info("Router '%s' carregado com sucesso.", _name)
    except Exception as exc:
        logger.error("ERRO ao importar router '%s' (%s): %s", _name, _module_path, exc)
        traceback.print_exc()


@app.get("/api/_debug/routers")
async def debug_routers():
    """
    Rota de diagnóstico: mostra quais routers subiram e quais rotas o
    FastAPI realmente registrou. Útil para depurar problemas de deploy
    direto pela URL, sem precisar de acesso aos logs da Vercel.
    """
    all_names = [name for name, _ in _ROUTER_MODULES]
    return {
        "loaded": sorted(_loaded_routers),
        "failed": sorted(set(all_names) - _loaded_routers),
        "routes": sorted({getattr(r, "path", str(r)) for r in app.routes}),
    }
