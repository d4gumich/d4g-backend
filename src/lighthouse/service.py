import os
import logging
import pdfplumber
from typing import Dict, Any, Optional
from huggingface_hub import HfApi, SpaceHardware
from gradio_client import Client
from src.shared.sanitizer import get_sanitizer
from src.core.config import settings

logger = logging.getLogger(__name__)

class LighthouseService:
    def __init__(self, repo_id: str = "Data4GoodCenter/resume_extraction_test"):
        self.repo_id = repo_id
        self.api = HfApi()
        self.hf_token = settings.HF_TOKEN
        
        if not self.hf_token:
            logger.warning("HF_TOKEN environment variable is not set. API calls might fail.")

    def analyze(self, text: str, sanitize: bool = False) -> Dict[str, Any]:
        try:
            if sanitize:
                logger.info("Sanitizing text before analysis...")
                text = get_sanitizer().redact(text)
                
            logger.info(f"Connecting to Lighthouse Space: {self.repo_id}")
            client = Client(self.repo_id, token=self.hf_token)
            
            result = client.predict(
                resume_text=text,
                api_name="/gradio_pipeline"
            )
            
            skills, top_jobs, recommendations = result
            
            return {
                "extracted_skills": skills,
                "top_jobs": top_jobs,
                "recommendations": recommendations,
                "status": "success"
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Lighthouse analysis failed: {error_msg}")
            
            if "queue" in error_msg.lower() or "limit" in error_msg.lower():
                return {
                    "error": "The Lighthouse service is currently under heavy load or usage limit reached. Please try again in 1-2 minutes.",
                    "status": "rate_limited"
                }
            elif "authentication" in error_msg.lower():
                return {
                    "error": "Authentication to Hugging Face failed. Please check backend configuration.",
                    "status": "auth_error"
                }
            
            return {"error": f"Analysis failed: {error_msg}", "status": "error"}

    def get_status(self) -> Dict[str, Any]:
        try:
            runtime = self.api.get_space_runtime(repo_id=self.repo_id)
            return {
                "stage": getattr(runtime, "stage", "UNKNOWN"),
                "hardware": self._format_hardware(runtime.hardware),
                "message": f"Successfully fetched status: {runtime.stage}"
            }
        except Exception as e:
            logger.error(f"Failed to get space status: {e}")
            return {"error": str(e), "stage": "ERROR", "hardware": "NULL"}

    def wake_up(self, hardware: SpaceHardware = SpaceHardware.T4_SMALL) -> Dict[str, Any]:
        try:
            logger.info(f"Wakeup request for {self.repo_id}")
            self.api.request_space_hardware(repo_id=self.repo_id, hardware=hardware, sleep_time=-1)
            # self.api.restart_space(repo_id=self.repo_id) # Optional: Sometimes hardware request is enough
            return self.get_status()
        except Exception as e:
            logger.error(f"Wakeup failed: {e}")
            return {"error": str(e), "stage": "ERROR", "hardware": "NULL"}

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
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def _format_hardware(self, obj: Any) -> str:
        if not obj: return "NULL"
        return getattr(obj, "current", str(obj))

lighthouse_service = LighthouseService()
