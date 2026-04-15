import logging
from typing import Any

import pdfplumber
from fastapi import HTTPException
from gradio_client import Client
from huggingface_hub import HfApi, SpaceHardware

from src.core.settings import settings
from src.shared.sanitizer import get_sanitizer

logger = logging.getLogger("uvicorn.error")


class LighthouseService:
    def __init__(self, repo_id: str = "Data4GoodCenter/resume_extraction_test"):
        self.repo_id = repo_id
        self.api = HfApi(token=settings.HF_TOKEN)
        self.hf_token = settings.HF_TOKEN

    def analyze(self, text: str, sanitize: bool = False) -> dict[str, Any]:
        try:
            if sanitize:
                logger.info("Sanitizing text before analysis...")
                text = get_sanitizer().redact(text)

            logger.info(f"Connecting to Lighthouse Space: {self.repo_id}")
            client = Client(self.repo_id, token=self.hf_token)

            result = client.predict(resume_text=text, api_name="/gradio_pipeline")
            skills, top_jobs, recommendations = result

            return {
                "extracted_skills": skills,
                "top_jobs": top_jobs,
                "recommendations": recommendations,
                "status": "success",
            }
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Lighthouse analysis failed: {e}")

            if "queue" in error_msg or "limit" in error_msg:
                raise HTTPException(
                    status_code=429,
                    detail="The Lighthouse service is currently under heavy load. Please try again in 1-2 minutes.",
                ) from e
            elif "authentication" in error_msg or "token" in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication to Hugging Face failed. Please check backend configuration.",
                ) from e

            raise HTTPException(
                status_code=502,
                detail=f"Downstream Lighthouse service failed: {e!s}",
            ) from e

    def get_status(self) -> dict[str, Any]:
        try:
            runtime = self.api.get_space_runtime(repo_id=self.repo_id)
            return {
                "stage": getattr(runtime, "stage", "UNKNOWN"),
                "hardware": self._format_hardware(runtime.hardware),
                "message": f"Successfully fetched status: {runtime.stage}",
            }
        except Exception as e:
            logger.error(f"Failed to get space status: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch Lighthouse status: {e!s}",
            ) from e

    def wake_up(self, hardware: SpaceHardware = SpaceHardware.T4_SMALL) -> dict[str, Any]:
        try:
            logger.info(f"Wakeup request for {self.repo_id}")
            # Request hardware and wake up from pause/sleep
            self.api.request_space_hardware(repo_id=self.repo_id, hardware=hardware, sleep_time=-1)
            # Explicitly restart to ensure server is running fresh
            self.api.restart_space(repo_id=self.repo_id)
            return self.get_status()
        except Exception as e:
            logger.error(f"Wakeup failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to wake up Lighthouse space: {e!s}",
            ) from e

    def pause_space(self) -> dict[str, Any]:
        try:
            logger.info(f"Pause request for {self.repo_id}")
            self.api.pause_space(repo_id=self.repo_id)
            return self.get_status()
        except Exception as e:
            logger.error(f"Pause failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to pause Lighthouse space: {e!s}",
            ) from e

    @staticmethod
    def parse_pdf(file_bytes: bytes, sanitize: bool = True) -> str:
        from io import BytesIO

        text = ""
        try:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"

            extracted = text.strip()
            if sanitize:
                logger.info("Sanitizing extracted PDF text")
                extracted = get_sanitizer().redact(extracted)

            return extracted
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Failed to extract text from PDF: {e!s}",
            ) from e

    def _format_hardware(self, obj: Any) -> str:
        if not obj:
            return "NULL"
        return getattr(obj, "current", str(obj))


lighthouse_service = LighthouseService()
