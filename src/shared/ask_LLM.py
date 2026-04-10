# -*- coding: utf-8 -*-
"""
Created on Sun Sep 21 16:06:12 2025

@author: XabUG07
"""

import google.generativeai as genai
from src.core.settings import settings

def ask_gemini(LLM_query_dict: dict):
    # ...
    # Get needed data from the parameters
    API_key = LLM_query_dict.get("my_API_key", None)
    query_LLM = LLM_query_dict["query_LLM"]

    LLM_response = ""

    # Get the key
    key = API_key or settings.GOOGLE_API_KEY

    if not key:
        return "⚠️ Google API key not configured."

    # Try with users API key if he sent one
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            query_LLM,  
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=800,
                temperature=0.0,
            ),
        )

        LLM_response = response.text

    except Exception as e:
        LLM_response = f"Try adding another API key, the response didn't work because: {e}"


    # Return the text content of the response
    return LLM_response