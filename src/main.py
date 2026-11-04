import logging
import time
from contextlib import asynccontextmanager

from a2wsgi import ASGIMiddleware
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.settings import settings
from src.shared.byok import LOGOUT_PATH, csrf_rejected, origin_rejected, tokens_match
from src.shared.log_safety import begin_request_log, current_request_id, finish_request_log, install_log_redaction
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
    install_log_redaction()
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
    from src.lighthouse.schedule_router import router as lighthouse_schedule_router
    from src.lighthouse.standard_router import router as lighthouse_standard_router
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
        if tokens_match(x_experimental_api_key, settings.EXPERIMENTAL_ACCESS_KEY):
            return
        raise HTTPException(status_code=403, detail="Invalid experimental access key or expired session.")

    app.include_router(auth_router, prefix="/api")
    app.include_router(chetah_router, prefix="/api")
    app.include_router(hangul_router, prefix="/api")
    app.include_router(owl_router, prefix="/api")
    app.include_router(summary_router, prefix="/api")
    app.include_router(lighthouse_standard_router, prefix="/api")

    if settings.ENABLE_EXPERIMENTAL:
        app.include_router(lighthouse_schedule_router, prefix="/api")
        app.include_router(lighthouse_router, prefix="/api", dependencies=[Depends(verify_experimental_key)])
        app.include_router(socrates_router, prefix="/api")

    # --- MIDDLEWARE STACK (Added in reverse order of execution) ---

    # 1. Logging Middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id, id_token, secret_token = begin_request_log(request.headers.get("x-request-id"))
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                logger.error(
                    "Unhandled exception ref=%s type=%s message=%s",
                    request_id,
                    type(exc).__name__,
                    exc,
                    exc_info=exc,
                )
                response = JSONResponse(
                    status_code=500,
                    content={
                        "message": "Something went wrong. Try again in a moment.",
                        "request_id": request_id,
                    },
                )
            response.headers["X-Request-ID"] = request_id
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "ref=%s method=%s path=%s status=%s %.2fms",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            return response
        finally:
            finish_request_log(id_token, secret_token)

    # 2. Proxy Header Trust (Mandatory for PythonAnywhere)
    # We remove the forced redirect to stop the loop, but keep the header trust
    # so that 'Secure' cookies and internal URL generation work correctly.
    @app.middleware("http")
    async def proxy_trust_middleware(request: Request, call_next):
        proxy_proto = request.headers.get("x-forwarded-proto", "").lower()
        if proxy_proto == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)

    @app.middleware("http")
    async def byok_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        own_origin = f"{request.url.scheme}://{request.url.netloc}"
        if origin_rejected(request.method, origin, [str(item) for item in settings.CORS_ORIGINS], own_origin):
            return JSONResponse(status_code=403, content={"detail": "Origin is not allowed."})
        if csrf_rejected(
            request.method,
            request.url.path,
            request.cookies.get("session_id"),
            request.cookies.get("lighthouse_session"),
            request.headers.get("x-csrf-token"),
            request.headers.get("x-lighthouse-csrf-token"),
        ):
            return JSONResponse(status_code=403, content={"detail": "CSRF token missing or invalid."})
        response = await call_next(request)
        if response.status_code < 400 and request.url.path != LOGOUT_PATH:
            from src.auth.router import refresh_session_cookies

            refresh_session_cookies(request, response)
        return response

    # 3. CORS Middleware (Outermost). Credentialed cookies need an explicit origin.
    # A wildcard cannot be combined with cookies, so an empty allowlist stays public
    # and non-credentialed.
    origins = [str(origin) for origin in settings.CORS_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=bool(origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "X-CSRF-Token",
            "X-Experimental-API-Key",
            "X-Force-Team-Key",
            "X-Lighthouse-CSRF-Token",
            "X-Request-ID",
            "X-Scheduler-Token",
        ],
        expose_headers=["X-Request-ID"],
    )

    # --- EXCEPTION HANDLING ---
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = current_request_id()
        logger.error(
            "Unhandled exception ref=%s type=%s message=%s",
            request_id,
            type(exc).__name__,
            exc,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "message": "Something went wrong. Try again in a moment.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    return app


app = create_app()
wsgi_app = ASGIMiddleware(app)
