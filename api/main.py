"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.routes import game, training, stats
from api.websocket import router as ws_router
from config import config

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    enabled=config.rate_limit.enabled,
    default_limits=[f"{config.rate_limit.requests_per_minute}/minute"],
)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


app = FastAPI(
    title="Blackjack Trainer",
    description="Professional blackjack card counting trainer API",
    version="0.1.0",
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.allowed_origins,
    allow_credentials=config.cors.allow_credentials,
    allow_methods=config.cors.allow_methods,
    allow_headers=config.cors.allow_headers,
)

@app.get("/api/health")
@limiter.limit(f"{config.rate_limit.requests_per_minute}/minute")
async def health_check(request: Request) -> dict[str, str]:
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
