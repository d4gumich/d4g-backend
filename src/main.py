import logging
import time
import traceback
from contextlib import asynccontextmanager

from a2wsgi import ASGIMiddleware
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.settings import settings
from src.shared.session import session_store

# Use the uvicorn logger to align with FastAPI's logging style
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    if settings.CORS_ORIGINS:
        logger.info(f"CORS origins configured: {settings.CORS_ORIGINS}")
    else:
        logger.warning("CORS_ORIGINS is empty. API will be inaccessible from browsers.")
    yield
    logger.info("Shutting down application...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Hello from d4g-backend (FastAPI)"}

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # --- ROUTES ---
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
        if lighthouse_session:
            session_data = session_store.get_session(lighthouse_session)
            if session_data and session_data.get("is_lighthouse"):
                return
        if settings.EXPERIMENTAL_ACCESS_KEY and x_experimental_api_key == settings.EXPERIMENTAL_ACCESS_KEY:
            return
        raise HTTPException(status_code=403, detail="Invalid experimental access key or expired session.")

    app.include_router(auth_router, prefix="/api")
    app.include_router(chetah_router, prefix="/api")
    app.include_router(hangul_router, prefix="/api")
    app.include_router(owl_router, prefix="/api")
    app.include_router(summary_router, prefix="/api")

    if settings.ENABLE_EXPERIMENTAL:
        app.include_router(lighthouse_router, prefix="/api", dependencies=[Depends(verify_experimental_key)])
        app.include_router(socrates_router, prefix="/api")

    # --- MIDDLEWARE STACK (Added in reverse order of execution) ---

    # 1. Logging Middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} {process_time:.2f}ms"
        )
        return response

    # 2. Proxy Header Trust (Mandatory for PythonAnywhere)
    # We remove the forced redirect to stop the loop, but keep the header trust
    # so that 'Secure' cookies and internal URL generation work correctly.
    @app.middleware("http")
    async def proxy_trust_middleware(request: Request, call_next):
        proxy_proto = request.headers.get("x-forwarded-proto", "").lower()
        if proxy_proto == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)

    # 3. CORS Middleware (Outermost)
    origins = settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in origins] if origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- EXCEPTION HANDLING ---
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

    return app


app = create_app()
wsgi_app = ASGIMiddleware(app)
