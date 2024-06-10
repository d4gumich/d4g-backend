from flask import Flask, request
from flask_cors import CORS
from chetah_v1 import search
import pandas as pd
import gc



    

app = Flask(__name__)
CORS(app)


    
    
BASE_PATH = '/api/v1/products'
BASE_PATH_SECOND_VERSION = '/api/v2/products'
CHETAH_PATH = f'{BASE_PATH}/chetah'
HANGUL_PATH = f'{BASE_PATH}/hangul'
HANGUL_SECOND_VERSION_PATH = f'{BASE_PATH_SECOND_VERSION}/hangul'
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

#endpoint for hangul 2.0
@app.post(HANGUL_SECOND_VERSION_PATH)
def hangul_second():
    # Get the current date and time
    now = pd.Timestamp.now()
    # Print dateTime in the format: yyyy-mm-dd HH:MM:SS
    print("----Running Hangul 2.0 on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    #num_pages = int(request.form['num_pages'])

    
    from hangul import detect_second_version
    
    result = detect_second_version(file, kw_num)

    del detect_second_version
    gc.collect()

    return result



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
    
    
    return generated_summary
