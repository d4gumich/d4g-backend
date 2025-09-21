# -*- coding: utf-8 -*-
"""
Created on Sun Sep 21 16:06:12 2025

@author: XabUG07
"""

import google.generativeai as genai

from secret import my_keys

# PUT YOUR GOOGLE API KEY IN THE FILE NAMED secret.py

def ask_gemini(LLM_query_dict: dict):
    
    """
    params LLM_query_dict: dict
    
    The dictionary needs to have minimum a key named "query_LLM", and 
    optionally the option to use your own key "my_API_key" 
    """
    
    
    # Start the model
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Get needed data from the parameters
    API_key = LLM_query_dict.get("my_API_key", None)
    query_LLM = LLM_query_dict["query_LLM"]
    
    LLM_response = ""
    
    # Get the key
    if API_key is None:
        key = my_keys()["Google_API_key"]
    else:
        key = API_key
        
        
    # Try with users API key if he sent one
    try:
        genai.configure(api_key=key)
        response = model.generate_content(
            query_LLM,  
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=800,
                temperature=0.0,
            ),
        )
        
        LLM_response = response.text
        
        
    # If first API key didn't work, try with internal
    except:
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            genai.configure(api_key=my_keys()["Google_API_key"])
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