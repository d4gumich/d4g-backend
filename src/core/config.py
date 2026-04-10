import os
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from configparser import ConfigParser

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "d4g-backend"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1/products"
    API_V2_STR: str = "/api/v2/products"
    
    # Storage
    UPLOAD_FOLDER: str = "uploads"
    DATASET_PATH: str = "dataset"
    
    # Owl DB Settings
    OWL_DB_HOST: str = "D4GUMSI-4679.postgres.pythonanywhere-services.com"
    OWL_DB_PORT: int = 14679
    OWL_DB_USER: str = "super"
    OWL_DB_NAME: str = "postgres"
    OWL_DB_PASSWORD: str | None = None
    
    # Secrets (Loaded from .env or environment)
    GOOGLE_API_KEY: str | None = None
    OWL_GOOGLE_API_KEY: str | None = None
    POSTGRESQL_PASS: str | None = None
    
    # Lighthouse
    HF_TOKEN: str | None = None
    
    # CORS
    CORS_ORIGINS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
