import asyncio
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from google.api_core import exceptions

logger = logging.getLogger(__name__)

T = TypeVar("T")


def async_retry(
    max_retries: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retry_on_exceptions: tuple = (
        exceptions.ResourceExhausted,
        exceptions.ServiceUnavailable,
        exceptions.InternalServerError,
    ),
):
    """
    Decorator for retrying async functions with exponential backoff.
    Specifically designed to handle Gemini API rate limits (429 ResourceExhausted).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    should_retry = False
                    if isinstance(e, retry_on_exceptions):
                        should_retry = True
                    elif "429" in str(e) or "Quota exceeded" in str(e):
                        should_retry = True

                    if not should_retry or attempt >= max_retries:
                        # Re-raise if we've exhausted retries or it's a non-retryable error
                        raise e

                    # Calculate jittered delay
                    current_delay = min(delay * (backoff_factor**attempt) + random.uniform(0, 1), max_delay)

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} after {current_delay:.2f}s "
                        f"due to error: {e}"
                    )

                    await asyncio.sleep(current_delay)

            # This part should theoretically not be reached due to the raise in the loop
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
