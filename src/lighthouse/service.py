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
        self._start_time: float | None = None

    def analyze(self, text: str, sanitize: bool = False) -> dict[str, Any]:
        try:
            if sanitize:
                logger.info("Sanitizing text before analysis...")
                text = get_sanitizer().redact(text)

            logger.info(f"Connecting to Lighthouse Space: {self.repo_id}")
            client = Client(self.repo_id, token=self.hf_token)

            result = client.predict(resume_text=text, api_name="/gradio_pipeline")
            skills, top_jobs, recommendations = result

            # Deduplicate skills (handles string or list input)
            if isinstance(skills, str):
                skill_list = [s.strip() for s in skills.split(",")]
            else:
                skill_list = [str(s).strip() for s in skills] if skills else []

            unique_skills = []
            seen = set()
            for s in skill_list:
                if isinstance(s, str) and s.strip().lower() not in seen:
                    unique_skills.append(s.strip())
                    seen.add(s.strip().lower())

            return {
                "extracted_skills": unique_skills,
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
            stage = getattr(runtime, "stage", "OFFLINE") or "OFFLINE"

            # Calculate elapsed time if booting
            elapsed = 0
            if stage != "RUNNING" and self._start_time:
                import time

                elapsed = int(time.time() - self._start_time)
            elif stage == "RUNNING":
                self._start_time = None  # Clear once running

            return {
                "stage": stage,
                "hardware": self._format_hardware(runtime.hardware),
                "message": f"Successfully fetched status: {stage}",
                "elapsed_seconds": elapsed,
            }
        except Exception as e:
            logger.error(f"Failed to get space status: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Could not fetch Lighthouse status: {e!s}",
            ) from e

    def wake_up(self, hardware: SpaceHardware = SpaceHardware.T4_SMALL) -> dict[str, Any]:
        try:
            import time

            self._start_time = time.time()
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

    def stop_space(self) -> dict[str, Any]:
        """
        Stop the space by requesting basic hardware (to release GPU) and pausing.
        """
        try:
            logger.info(f"Stop request for {self.repo_id}")
            # Step 1: Request CPU basic to release GPU resources
            self.api.request_space_hardware(repo_id=self.repo_id, hardware=SpaceHardware.CPU_BASIC)
            # Step 2: Pause the space
            self.api.pause_space(repo_id=self.repo_id)
            return self.get_status()
        except Exception as e:
            logger.error(f"Stop failed: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to stop Lighthouse space: {e!s}",
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
