from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
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
