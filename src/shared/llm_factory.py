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
                    # banana/nano/lyria are internal/experimental codenames
                    internal_keywords = [
                        "tts",
                        "custom-tools",
                        "robotics",
                        "antigravity",
                        "clip",
                        "banana",
                        "nano",
                        "lyria",
                        "internal",
                        "experimental",
                        "thinking",
                        "image",
                    ]

                    # Check both the technical ID and the display name for internal keywords
                    full_text = (model_id + " " + display_name).lower()
                    is_internal = any(x in full_text for x in internal_keywords)

                    # 2. Whitelist check for production-ready patterns
                    # Case-insensitive startswith check
                    mid_lower = model_id.lower()
                    is_prod = any(mid_lower.startswith(p) for p in whitelist)

                    if is_prod and not is_internal:
                        # 3. Categorize tier (Flash and Lite are Free Tier)
                        is_free = any(x in full_text for x in ["flash", "lite"])
                        tier = "free" if is_free else "paid"
                        available.append({"id": model_id, "name": display_name, "tier": tier})

            # Sort by version (descending) to show newest first
            available.sort(key=lambda x: x["id"], reverse=True)
            return available

        elif "openai" in provider:
            # Static list for now as dynamic listing includes many non-chat models
            return [
                {"id": "gpt-4o", "name": "GPT-4o (High Quality)"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Fast)"},
                {"id": "o1-mini", "name": "o1-mini (Reasoning)"},
            ]

        elif "anthropic" in provider or "claude" in provider:
            return [
                {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet (Balanced)"},
                {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku (Fast)"},
                {"id": "claude-3-opus-latest", "name": "Claude 3 Opus (Reasoning)"},
            ]

        return []
    except Exception as e:
        logger.error(f"Failed to fetch models for {provider}: {e}")
        raise e


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

    # If api_key is None in session, it's a Team Key session
    if not api_key:
        if "google" in provider or "gemini" in provider:
            api_key = settings.GOOGLE_API_KEY
        else:
            raise ValueError(f"Team key session not supported for provider {provider}")

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
    # Ensure global state is set to the BACKEND key before the fallback call
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    return await _call_gemini(settings.GOOGLE_API_KEY, settings.SOCRATES_STANDARD_MODEL, prompt, system, mime)
