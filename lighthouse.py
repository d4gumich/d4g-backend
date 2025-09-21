# -*- coding: utf-8 -*-
"""
Created on Sat Sep 20 14:20:52 2025

@author: XabUG07
"""


import fitz
from fastapi import UploadFile

import ask_LLM


# -------------------- LIGHTHOUSE --------------------

def enlighten_me(cv_file: UploadFile, query_dict: dict):
    
    
    """
    query_dict @dict: a dictionary that contains the query and all parameters related to it
    """   
    
    
    # Open PDF with FITZ
    pdf = fitz.open(stream=cv_file.stream.read(), filetype="pdf")
    

    # This extracts the content of the pdf
    content_as_pages = [page.get_text("text") for page in pdf]
    cleaned_content = ''.join(content_as_pages)
    
    
    # The final query combines the predefined text and the CV content
    query_dict["query_LLM"]  = query_dict["CV_query"] + ": " + cleaned_content
    
    carrer_advice = ask_LLM.ask_gemini(query_dict)

    
    
    return {
        'CV_content': cleaned_content,
        "lighthouse_response": carrer_advice,
        "full_query": query_dict,

    }