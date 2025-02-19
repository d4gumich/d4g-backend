from flask import Flask, request
from flask_cors import CORS
from chetah_v1 import search
import chetah_v2
import pandas as pd
import gc


import psutil


def monitor_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    rss_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
    print(f"Memory usage: {rss_mb:.2f} MB")
    

app = Flask(__name__)
CORS(app)


    
BASE_PATH = '/api/v1/products'
BASE_PATH_SECOND_VERSION = '/api/v2/products'
CHETAH_PATH = f'{BASE_PATH}/chetah'
CHETAH_PATH_SECOND_VERSION = f'{BASE_PATH_SECOND_VERSION}/chetah'
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
    # Print dateTime in the format: yyyy-mm-dd HH:MM:SS
    print("----Running Hangul 2.0 on ", now.strftime("%Y-%m-%d %H:%M:%S"), "------")
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    #num_pages = int(request.form['num_pages'])

    
    from hangul import detect_second_version
    
    result = detect_second_version(file, kw_num)

    del detect_second_version
    gc.collect()
    
    print("Memory usage after Hangul 2.0 first API call:")
    monitor_memory_usage()
    
    return result

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
