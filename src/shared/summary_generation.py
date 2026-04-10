# SUMMARY GENERATION
# @author: Xabier Urruchua Garay


import google.generativeai as genai

from secret import my_keys

# PUT YOUR GOOGLE API KEY IN THE FILE NAMED secret.py

def make_summary_with_API(all_content, API_key=None):
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Get the key
    if API_key is None:
        key = my_keys()["Google_API_key"]
    else:
        key = API_key
    
    genai.configure(api_key=key)
    response = model.generate_content(
        f"Summarize the following text into a concise and structured format: {all_content}",  
        generation_config=genai.types.GenerationConfig(
            candidate_count=1,
            max_output_tokens=800,
            temperature=0.0,
        ),
    )

    # Return the text content of the response
    return response.text



# def make_summary_with_API(all_content):
#     document_content = all_content
#     genai.configure(api_key="YOUR KEY HERE")
#     model = genai.GenerativeModel("gemini-2.0-flash-lite-preview-02-05")
#     response = model.generate_content(
#     f"Summarize this content: {document_content}",
#     generation_config=genai.types.GenerationConfig(
#         candidate_count=1,
#         max_output_tokens=800,
#         temperature=0.0,
#         top_p=1,
#         top_k=0,
#         # seed=1,
#     ),
# )
#     # Return the text content of the response
#     return response.text