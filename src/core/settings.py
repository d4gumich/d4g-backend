import os
from configparser import ConfigParser

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "d4g-backend"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENABLE_EXPERIMENTAL: bool = True
    EXPERIMENTAL_ACCESS_KEY: str | None = None
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1/products"
    API_V2_STR: str = "/api/v2/products"

    # Infrastructure
    PROXY_HEADERS: bool = True

    # Storage
    UPLOAD_FOLDER: str = "uploads"
    DATASET_PATH: str = "dataset"

    # Owl DB Settings
    OWL_DB_HOST: str | None = "D4GUMSI-4679.postgres.pythonanywhere-services.com"
    OWL_DB_PORT: int = 14679
    OWL_DB_USER: str | None = "super"
    OWL_DB_NAME: str = "postgres"
    OWL_DB_PASSWORD: str | None = None

    # Chetah Settings
    CHETAH_DATASET_PATH: str = "dataset/final_with_cluster.csv"
    CHETAH_INV_PATH: str = "dataset/inv_index.json"
    CHETAH_DOC_PATH: str = "dataset/doc_table.json"

    # Model Paths (Relative to project root)
    THEME_MODEL_PATH: str = "src/shared/models/Model_RW_ThemeDetect.pkl"
    THEME_VECTORIZER_PATH: str = "src/shared/models/Vectorizer_RW_ThemeDetect.pkl"
    DISASTER_MODEL_PATH: str = "src/shared/models/disaster_detection_NN.pth"
    DISASTER_VECTORIZER_PATH: str = "src/shared/models/tfidf_vectorizer_disaster.pkl"

    # Secrets (Loaded from .env or environment)
    GOOGLE_API_KEY: str | None = None
    OWL_GOOGLE_API_KEY: str | None = None
    POSTGRESQL_PASS: str | None = None

    # Lighthouse
    HF_TOKEN: str | None = None

    # CORS
    CORS_ORIGINS: list[str] = []

    # Socrates Settings
    SOCRATES_DB_URL: str | None = None
    SOCRATES_DEEP_MODEL: str = "gemini-3.1-pro-preview"
    SOCRATES_STANDARD_MODEL: str = "gemini-2.5-flash-lite"
    SOCRATES_LIGHT_MODEL: str = "gemini-3.1-flash-preview"

    # Use an absolute path for the .env file to ensure it's found regardless of the CWD
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        extra="ignore",
    )

    def load_ini_config(self, ini_path: str = "configuration.ini") -> None:
        """Loads additional configuration from .ini file if it exists."""
        if os.path.exists(ini_path):
            config = ConfigParser()
            config.read(ini_path)
            # Add custom logic to map ini values if needed
            # For example, Chetah paths are in the ini file


settings = Settings()
# Ensure upload folder exists
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
