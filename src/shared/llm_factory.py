import logging
import os

from src.core.settings import settings
from src.shared.session import session_store

logger = logging.getLogger(__name__)


async def validate_key(provider: str, model_name: str, api_key: str) -> tuple[bool, str]:  # noqa: PLR0911
    """
    Validates the API key by performing a real network request.
    Returns (is_valid, error_message).
    """
    provider = provider.lower()
    try:
        if "google" in provider or "gemini" in provider:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            # Authenticate by listing models. This is the most reliable way
            # to verify a KEY without being tied to specific model availability.
            try:
                # Force iteration to ensure a network request is made
                models = genai.list_models()
                for _ in models:
                    return True, ""
                return False, "Key is valid but no models are available for this project."
            except Exception as e:
                # If list_models fails, the key is almost certainly invalid or restricted
                error_msg = str(e)
                if "401" in error_msg or "403" in error_msg or "API_KEY_INVALID" in error_msg:
                    return False, f"Invalid or unauthorized API key: {error_msg}"
                raise e

        elif "openai" in provider:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            # Lightweight call to verify the key
            client.models.list()
            return True, ""

        elif "anthropic" in provider or "claude" in provider:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            # Use a fast model for validation
            validation_model = model_name or "claude-3-5-haiku-latest"
            client.messages.create(model=validation_model, max_tokens=1, messages=[{"role": "user", "content": "ping"}])
            return True, ""

        return False, "Unsupported provider"
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Key validation failed for {provider}: {error_msg}")
        return False, error_msg


async def fetch_available_models(provider: str, api_key: str | None = None) -> list[dict[str, str]]:
    """
    Fetches the list of available models for a given provider and API key.
    """
    provider = provider.lower()
    try:
        if "google" in provider or "gemini" in provider:
            import google.generativeai as genai

            # Use provided key or fall back to backend key
            key = api_key or settings.GOOGLE_API_KEY
            if not key:
                raise ValueError("No Google API key available.")

            genai.configure(api_key=key)
            models = genai.list_models()
            available = []

            # Whitelist of production-ready Gemini model prefixes/patterns
            whitelist = [
                "gemini-3.5-flash",
                "gemini-3.1-flash",
                "gemini-3.1-pro",
                "gemini-3-flash",
                "gemini-3-pro",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ]

            for m in models:
                # Filter for models that support generating content
                if "generateContent" in m.supported_generation_methods:
                    model_id = m.name.replace("models/", "")
                    display_name = m.display_name

                    # 1. Block internal/experimental codenames (Case-Insensitive)
                    internal_keywords = [
                        "tts",
                        "custom-tools",
                        "robotics",
                        "antigravity",
                        "clip",
                        "vision",
                        "embedding",
                        "aqa",
                    ]
                    if any(kw in model_id.lower() for kw in internal_keywords):
                        continue

                    # 2. Match against whitelist or production patterns
                    is_whitelisted = any(model_id.startswith(p) for p in whitelist)
                    # Also include anything clearly marked as experimental if whitelisted
                    if is_whitelisted:
                        # Extract tier (Pro vs Flash)
                        tier = "Pro" if "pro" in model_id.lower() else "Flash"
                        available.append({"id": model_id, "name": display_name, "tier": tier})

            # Sort by name, newest first (rough heuristic)
            return sorted(available, key=lambda x: x["id"], reverse=True)

        elif "openai" in provider:
            from openai import OpenAI

            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                return []
            client = OpenAI(api_key=key)
            models = client.models.list()
            # Filter for common GPT models
            available = []
            for m in models:
                if m.id.startswith("gpt-"):
                    available.append({"id": m.id, "name": m.id.upper(), "tier": "Pro"})
            return available

        elif "anthropic" in provider or "claude" in provider:
            # Anthropic doesn't have a simple 'list models' API like the others
            return [
                {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet", "tier": "Pro"},
                {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku", "tier": "Flash"},
                {"id": "claude-3-opus-latest", "name": "Claude 3 Opus", "tier": "Pro"},
            ]

        return []
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {e}")
        return []


async def call_llm(
    prompt: str,
    system_instruction: str | None = None,
    response_mime_type: str = "text/plain",
    session_id: str | None = None,
) -> str:
    """
    Unified entry point for LLM calls.
    Handles session retrieval, key selection, and error handling.
    """
    if session_id:
        session_data = session_store.get_session(session_id)
        if session_data and session_data.get("api_key"):
            # Personal Key Path
            provider = session_data.get("provider", "google")
            model_id = session_data.get("selected_model", settings.SOCRATES_STANDARD_MODEL)
            api_key = session_data.get("api_key")

            if "google" in provider.lower() and isinstance(api_key, str):
                return await _call_gemini_with_key(prompt, api_key, model_id, system_instruction, response_mime_type)
            # Add other providers here as needed

    # Fallback to Team Key / Backend Key
    return await _call_gemini_fallback(prompt, system_instruction, response_mime_type)


async def _call_gemini_with_key(prompt: str, api_key: str, model_id: str, system: str | None, mime: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_id,
        system_instruction=system,
    )
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type=mime,
        ),
    )
    return response.text


async def _call_gemini_fallback(prompt: str, system: str | None, mime: str) -> str:
    """Uses the default backend Gemini key if no session is active."""
    if not settings.GOOGLE_API_KEY:
        raise ValueError("Default Google API key not configured.")
    import google.generativeai as genai

    # Ensure global state is set to the BACKEND key before the fallback call
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    model_id = settings.SOCRATES_STANDARD_MODEL
    model = genai.GenerativeModel(
        model_id,
        system_instruction=system,
    )
    response = await model.generate_content_async(
        prompt,
        generation_config=genai.types.GenerationConfig(
            response_mime_type=mime,
        ),
    )
    return response.text
