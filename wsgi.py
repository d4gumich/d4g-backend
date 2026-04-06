from flask import Flask, request, jsonify
from flask_cors import CORS
from chetah_v1 import search
import chetah_v2
import owl
import pandas as pd
import gc

# New imports for Lighthouse
from lighthouse import Lighthouse
lighthouse_inst = Lighthouse()
from werkzeug.utils import secure_filename
import os


import psutil


def monitor_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    rss_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
    print(f"Memory usage: {rss_mb:.2f} MB")
    

app = Flask(__name__)
CORS(app)


# Define a folder to store uploaded files temporarily
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    
BASE_PATH = '/api/v1/products'
BASE_PATH_SECOND_VERSION = '/api/v2/products'
CHETAH_PATH = f'{BASE_PATH}/chetah'
CHETAH_PATH_SECOND_VERSION = f'{BASE_PATH_SECOND_VERSION}/chetah'
HANGUL_PATH = f'{BASE_PATH}/hangul'
HANGUL_SECOND_VERSION_PATH = f'{BASE_PATH_SECOND_VERSION}/hangul'
OWL_PATH = f'{BASE_PATH}/owl'
LIGHTHOUSE_BASE_PATH = f'{BASE_PATH}/lighthouse'
SUMMARY_GENERATION_PATH = f'{BASE_PATH_SECOND_VERSION}/summary'


@app.post(CHETAH_PATH)
def chetah():
    # Get the current date and time
    now = pd.Timestamp.now()
    # Print dateTime in the format: yyyy-mm-dd HH:MM:SS
    print("----Running Chetah on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    body = request.get_json()
    query = body['query']
    return search(query)

gc.collect()

@app.post(CHETAH_PATH_SECOND_VERSION)
def chetah_second():
    # Get the current date and time
    now = pd.Timestamp.now()
    # Print dateTime in the format: yyyy-mm-dd HH:MM:SS
    print("----Running Chetah 2.0 on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    body = request.get_json()
    query = body['query']
    return chetah_v2.search(query)

gc.collect()


@app.post(HANGUL_PATH)
def hangul():
    # Get the current date and time
    now = pd.Timestamp.now()
    # Print dateTime in the format: yyyy-mm-dd HH:MM:SS
    print("----Running Hangul 1.0 on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    from hangul import detect
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    result = detect(file, kw_num)
    del detect
    gc.collect()
    
    return result

gc.collect()


#endpoint for hangul 2.0
@app.post(HANGUL_SECOND_VERSION_PATH)
def hangul_second():
    # Get the current date and time
    now = pd.Timestamp.now()
    print("----Running Hangul 2.0 on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    API_key = request.form.get("my_API_key", None)
    instruct_dict = request.form.to_dict(flat=True)

    
    from hangul import detect_second_version
    
    result = detect_second_version(file, kw_num, API_key, instruct_dict)

    del detect_second_version
    gc.collect()
    
    print("Memory usage after Hangul 2.0 API call:")
    monitor_memory_usage()
    
    return result

gc.collect()


@app.route(f'{LIGHTHOUSE_BASE_PATH}/wakeup', methods=['POST'])
def wakeup_lighthouse():
    """Wakes up the Lighthouse Hugging Face Space."""
    print("----Waking up Lighthouse Space----")
    try:
        return jsonify(lighthouse_inst.wake_up()), 200
    except Exception as e:
        print(f"Error waking up Lighthouse: {e}")
        return jsonify({"error": str(e)}), 500

@app.get(f'{LIGHTHOUSE_BASE_PATH}/status')
def get_lighthouse_status():
    """Gets the status of the Lighthouse Hugging Face Space."""
    print("----Getting Lighthouse Space Status----")
    try:
        return jsonify(lighthouse_inst.get_status()), 200
    except Exception as e:
        print(f"Error getting Lighthouse status: {e}")
        return jsonify({"error": str(e)}), 500

@app.post(f'{LIGHTHOUSE_BASE_PATH}/analyze-text')
def analyze_lighthouse_text():
    """
    Accepts raw text and performs analysis using Lighthouse.
    Input: JSON {"resume_text": "..."} or Form Data
    """
    print("----Analyzing Text via Lighthouse----")
    try:
        body = request.get_json(force=True, silent=True) or {}
        text = body.get('resume_text') or request.form.get('resume_text')
        sanitize = body.get('sanitize', False) or (request.form.get('sanitize', 'false').lower() == 'true')
        
        if not text:
            return jsonify({"error": "Missing text (resume_text) in request body or form"}), 400
            
        result = lighthouse_inst.analyze(text, sanitize=sanitize)
        return jsonify(result), 200
    except Exception as e:
        print(f"Error during Lighthouse analysis: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500

@app.post(f'{LIGHTHOUSE_BASE_PATH}/parse-pdf')
def parse_pdf_test():
    """
    Test route to parse a PDF using pdfplumber.
    Input: File upload 'file'
    """
    print("----Testing PDF Parser (pdfplumber)----")
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Check for sanitize flag
        sanitize = request.form.get('sanitize', 'false').lower() == 'true'
        
        try:
            # Parse PDF
            extracted_text = Lighthouse.parse_pdf(file_path, sanitize=sanitize)
            
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return jsonify({
                "status": "success",
                "extracted_text": extracted_text,
                "length": len(extracted_text)
            }), 200
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"PDF parsing failed: {e}")
            return jsonify({"error": str(e)}), 500


# Endpoint for OWL
@app.post(OWL_PATH)
def owl_chatbot():
    # Get the current date and time
    now = pd.Timestamp.now()
    # Print dateTime in the format: yyyy-mm-dd HH:MM:SS
    print("----Running Owl on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    body = request.get_json()

    return owl.ask_owl(body)

gc.collect()


@app.post(SUMMARY_GENERATION_PATH)
def summary_second():
    
    summary_parameters_dic = request.get_json()
    
    summary_parameters = (summary_parameters_dic["ranked_sentences"],
                          summary_parameters_dic["themes_detected"],
                          summary_parameters_dic["top_locations"],
                          summary_parameters_dic["_detected_disasters"])
    
    import summary_generation
    
    agg_summary_input = summary_generation.combine_all_metadata_into_input(*summary_parameters)
    
    generated_summary = summary_generation.recursive_summarize(agg_summary_input)
    
    
    del summary_generation
    gc.collect()
    
    
    print("Memory usage after Hangul 2.0 second API call:")
    monitor_memory_usage()
    
    return generated_summary

gc.collect()

@app.get('/')
def index():
    return "Hello World"
