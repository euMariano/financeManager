"""API do Organizador Financeiro - MVP."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import create_db_and_tables
from app.routers import auth, balance, cards, export

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Finance Manager API",
    description="API de CRUD para organizador financeiro: saldo líquido, cards de despesas, faixa (vermelho/amarelo/verde) e exportação em planilha.",
    version="0.1.0",
    lifespan=lifespan,
)

# API sob /api para não conflitar com arquivos estáticos
app.include_router(auth.router, prefix="/api")
app.include_router(balance.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(export.router, prefix="/api")

# Frontend em /app para não sobrescrever /docs e /openapi.json
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    @app.get("/")
    def root_redirect():
        return RedirectResponse(url="/app/")
