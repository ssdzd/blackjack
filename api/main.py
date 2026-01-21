"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes import game, training, stats
from api.websocket import router as ws_router

app = FastAPI(
    title="Blackjack Trainer",
    description="Professional blackjack card counting trainer API",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(training.router, prefix="/api/training", tags=["training"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])

# Mount static files (must be last since it's a catch-all)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")
