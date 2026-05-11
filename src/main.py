import logging
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Cookie, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.settings import settings
from src.shared.session import session_store

# Use the uvicorn logger to align with FastAPI's logging style (colors, etc.)
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} (DEBUG={settings.DEBUG})")

    # Verify settings are loaded
    if settings.HF_TOKEN:
        logger.info("Hugging Face token loaded successfully.")
    else:
        logger.warning("HF_TOKEN is missing in environment/settings.")

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

    from fastapi import Header, HTTPException

    from src.auth.router import router as auth_router
    from src.chetah.router import router as chetah_router
    from src.hangul.router import router as hangul_router
    from src.lighthouse.router import router as lighthouse_router
    from src.owl.router import router as owl_router
    from src.socrates.router import router as socrates_router
    from src.summary.router import router as summary_router

    async def verify_experimental_key(
        x_experimental_api_key: str = Header(None), lighthouse_session: str = Cookie(None)
    ):
        # Case 1: Session Cookie (Secure/XSS-proof)
        if lighthouse_session:
            session_data = session_store.get_session(lighthouse_session)
            if session_data and session_data.get("is_lighthouse"):
                return
            else:
                logger.info(f"Lighthouse session found but was invalid or expired: {lighthouse_session}")

        # Case 2: Direct Header (Legacy/Direct API)
        if x_experimental_api_key == settings.EXPERIMENTAL_ACCESS_KEY:
            return

        logger.info(
            f"Unauthorized access attempt. Key header provided: {bool(x_experimental_api_key)}, Session cookie provided: {bool(lighthouse_session)}"
        )
        raise HTTPException(status_code=403, detail="Invalid experimental access key or expired session.")

    app.include_router(auth_router, prefix="/api")
    app.include_router(chetah_router, prefix="/api")
    app.include_router(hangul_router, prefix="/api")
    app.include_router(owl_router, prefix="/api")
    app.include_router(summary_router, prefix="/api")

    # Gate experimental features
    if settings.ENABLE_EXPERIMENTAL:
        logger.info("Experimental features (Lighthouse, Socrates) enabled.")
        app.include_router(lighthouse_router, prefix="/api", dependencies=[Depends(verify_experimental_key)])
        # Socrates is now BYOK, so we remove the mandatory team access key
        app.include_router(socrates_router, prefix="/api")
    else:
        logger.info("Experimental features disabled. Use ENABLE_EXPERIMENTAL=true to enable.")

    return app


app = create_app()
