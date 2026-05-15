import logging

import google.generativeai as genai
from anthropic import Anthropic
from openai import OpenAI

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
            client = OpenAI(api_key=api_key)
            # Lightweight call to verify the key
            client.models.list()
            return True, ""

        elif "anthropic" in provider or "claude" in provider:
            client = Anthropic(api_key=api_key)
            # Smallest possible message to verify the key
            client.messages.create(model=model_name, max_tokens=1, messages=[{"role": "user", "content": "ping"}])
            return True, ""

        return False, "Unsupported provider"
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Key validation failed for {provider}: {error_msg}")
        return False, error_msg


async def call_llm(
    prompt: str,
    session_id: str | None = None,
    system_instruction: str | None = None,
    response_mime_type: str = "text/plain",
) -> str:
    """
    Unified LLM caller that handles BYOK sessions and multiple providers.
    """
    if not session_id:
        return await _call_gemini_fallback(prompt, system_instruction, response_mime_type)

    session_data = session_store.get_session(session_id)
    if not session_data:
        raise ValueError("Invalid or expired session. Please log in again.")

    provider = str(session_data.get("provider", "")).lower()
    model_name = str(session_data.get("selected_model", ""))
    api_key = session_data.get("api_key")

    if not api_key or not isinstance(api_key, str):
        raise ValueError(f"API key missing for provider {provider}")

    try:
        if "google" in provider or "gemini" in provider:
            # Ensure global state is set to THIS session's key before the call
            genai.configure(api_key=api_key)
            return await _call_gemini(api_key, model_name, prompt, system_instruction, response_mime_type)
        elif "openai" in provider:
            return await _call_openai(api_key, model_name, prompt, system_instruction, response_mime_type)
        elif "anthropic" in provider or "claude" in provider:
            return await _call_anthropic(api_key, model_name, prompt, system_instruction)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    except Exception as e:
        logger.error(f"LLM call failed ({provider}/{model_name}): {e}")
        # If we get a 404 for a specific model ID, it might be that the model ID
        # needs the 'models/' prefix or is simply not available.
        raise e


async def _call_gemini(api_key: str, model_name: str, prompt: str, system: str | None, mime: str) -> str:
    # Use the model name as provided (e.g., 'gemini-1.5-flash')
    # The SDK handles namespacing internally.
    model = genai.GenerativeModel(model_name=model_name, system_instruction=system)

    config = genai.types.GenerationConfig(
        candidate_count=1, max_output_tokens=2048, temperature=0.1, response_mime_type=mime
    )

    response = await model.generate_content_async(prompt, generation_config=config)
    return response.text


async def _call_openai(api_key: str, model_name: str, prompt: str, system: str | None, mime: str) -> str:
    client = OpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response_format = {"type": "json_object"} if mime == "application/json" else None

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format=response_format,
        temperature=0.1,  # type: ignore[arg-type]
    )
    return response.choices[0].message.content  # type: ignore[return-value]


async def _call_anthropic(api_key: str, model_name: str, prompt: str, system: str | None) -> str:
    client = Anthropic(api_key=api_key)

    # Claude handles system prompts differently
    response = client.messages.create(
        model=model_name,
        max_tokens=2048,
        system=system if system else "",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    # Claude doesn't have a specific response_mime_type in the SDK like Gemini,
    # but we can rely on prompting for JSON.
    return response.content[0].text  # type: ignore[return-value]


async def _call_gemini_fallback(prompt: str, system: str | None, mime: str) -> str:
    """Uses the default backend Gemini key if no session is active."""
    if not settings.GOOGLE_API_KEY:
        raise ValueError("Default Google API key not configured.")
    return await _call_gemini(settings.GOOGLE_API_KEY, settings.SOCRATES_STANDARD_MODEL, prompt, system, mime)
