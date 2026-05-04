"""
Created on Sun Sep 21 16:06:12 2025

@author: XabUG07
"""

import logging

from src.shared.llm_factory import call_llm

logger = logging.getLogger(__name__)


async def ask_gemini(LLM_query_dict: dict):
    """
    Refactored to use the central llm_factory.
    Supports session-based BYOK if session_id is provided.
    """
    query_LLM = LLM_query_dict.get("query_LLM")
    session_id = LLM_query_dict.get("session_id")

    if not query_LLM:
        return "⚠️ No query provided."

    try:
        response = await call_llm(prompt=query_LLM, session_id=session_id)
        return response
    except Exception as e:
        return f"Error communicating with AI: {e}"
