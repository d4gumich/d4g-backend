import os
import logging
import pdfplumber
from huggingface_hub import HfApi, SpaceHardware
import dotenv
from gradio_client import Client
from sanitizer import get_sanitizer

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class Lighthouse:
    """
    Manages interactions with the Hugging Face Space for Lighthouse analysis.
    Provides methods for status checks, hardware wakeup, and text analysis.
    """
    
    def __init__(self, repo_id="Data4GoodCenter/resume_extraction_test"):
        self.repo_id = repo_id
        self.api = HfApi()
        self.hf_token = os.getenv("HF_TOKEN")
        
        if not self.hf_token:
            logger.warning("HF_TOKEN environment variable is not set. API calls might fail.")

    def analyze(self, text, sanitize=False):
        """
        Connects to the Gradio space and performs prediction on provided text.
        
        Args:
            text (str): Content to analyze (e.g., extracted resume text).
            sanitize (bool): If True, redact PII before sending for analysis.
            
        Returns:
            dict: Structured results or error message.
        """
        try:
            if sanitize:
                logger.info("Sanitizing text before analysis...")
                text = get_sanitizer().redact(text)
                
            logger.info(f"Connecting to Lighthouse Space: {self.repo_id}")
            # Optimized: Using a single client call for prediction
            client = Client(self.repo_id, token=self.hf_token)
            
            # Predict using the specific named endpoint from your app.py
            result = client.predict(
                resume_text=text,
                api_name="/gradio_pipeline"
            )
            
            # Unpack results: (extracted_skills, top_jobs, recommendations)
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
            
            # Gracious handling for common HF/Gradio limits
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

    def get_status(self):
        """Retrieves current runtime status of the space."""
        try:
            runtime = self.api.get_space_runtime(repo_id=self.repo_id)
            return {
                "stage": getattr(runtime, "stage", "UNKNOWN"),
                "hardware": self._format_hardware(runtime.hardware),
                "message": f"Successfully fetched status: {runtime.stage}"
            }
        except Exception as e:
            logger.error(f"Failed to get space status: {e}")
            return {"error": str(e), "stage": "ERROR"}

    def wake_up(self, hardware=SpaceHardware.T4_SMALL):
        """Attempts to wake up the space if it's sleeping."""
        try:
            logger.info(f"Wakeup request for {self.repo_id}")
            self.api.request_space_hardware(repo_id=self.repo_id, hardware=hardware, sleep_time=-1)
            self.api.restart_space(repo_id=self.repo_id)
            return self.get_status()
        except Exception as e:
            logger.error(f"Wakeup failed: {e}")
            return {"error": str(e), "stage": "ERROR"}

    @staticmethod
    def parse_pdf(file_path, sanitize=True):
        """
        Extracts text from a PDF file using pdfplumber.
        
        Args:
            file_path (str): Path to the PDF file.
            sanitize (bool): Whether to redact PII from the extracted text.
            
        Returns:
            str: Extracted text content.
        """
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"
            
            extracted = text.strip()
            if sanitize:
                logger.info(f"Sanitizing extracted PDF text from {file_path}")
                extracted = get_sanitizer().redact(extracted)
                
            return extracted
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def _format_hardware(self, obj):
        if not obj: return "NULL"
        return getattr(obj, "current", str(obj))
