import logging
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.settings import settings

# Use the uvicorn logger to align with FastAPI's logging style (colors, etc.)
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} (DEBUG={settings.DEBUG})")

    yield

    # Shutdown: Cleanup resources
    logger.info("Shutting down application...")
    try:
        # Tika server can sometimes block Ctrl+C if not handled
        import tika

        tika.tika.killServer()
        logger.info("Tika server stopped.")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error stopping Tika server: {e}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # Set all CORS enabled origins
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Middleware for request logging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}"
        logger.info(
            f"Method: {request.method} Path: {request.url.path} "
            f"Status: {response.status_code} Time: {formatted_process_time}ms"
        )
        return response

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")

        error_content: dict[str, Any] = {"message": "Internal Server Error"}
        if settings.DEBUG:
            error_content["detail"] = str(exc)
            error_content["traceback"] = traceback.format_exc().splitlines()

        return JSONResponse(
            status_code=500,
            content=error_content,
        )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Hello from d4g-backend (FastAPI)"}

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    from src.chetah.router import router as chetah_router
    from src.hangul.router import router as hangul_router
    from src.lighthouse.router import router as lighthouse_router
    from src.owl.router import router as owl_router
    from src.summary.router import router as summary_router

    app.include_router(chetah_router, prefix="/api")
    app.include_router(hangul_router, prefix="/api")
    app.include_router(lighthouse_router, prefix="/api")
    app.include_router(owl_router, prefix="/api")
    app.include_router(summary_router, prefix="/api")

    return app


app = create_app()
