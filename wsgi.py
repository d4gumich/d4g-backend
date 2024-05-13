from flask import Flask, request
from flask_cors import CORS
from chetah_v1 import search
import gc
#from hangul import detect_second_version #detect
import psutil
import sys


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
HANGUL_PATH = f'{BASE_PATH}/hangul'
HANGUL_SECOND_VERSION_PATH = f'{BASE_PATH_SECOND_VERSION}/hangul'
SUMMARY_GENERATION_PATH = f'{BASE_PATH_SECOND_VERSION}/summary'


@app.post(CHETAH_PATH)
def chetah():
    body = request.get_json()
    print(body)
    query = body['query']
    return search(query)


# @app.post(HANGUL_PATH)
# def hangul():
#     file = request.files['file']
#     kw_num = int(request.form['kw_num'])
#     return detect(file, kw_num)

#endpoint for hangul 2.0
@app.post(HANGUL_SECOND_VERSION_PATH)
def hangul_second():
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    
    print("Memory usage of imports:")
    monitor_memory_usage()
    
    import hangul
    
    result = hangul.detect_second_version(file, kw_num)
    # summary_parameters = result["document_summary"]
    # result["document_summary"] = ""
    
    # print("refs hangul: ", sys.getrefcount(hangul))
    # print("refs hangul 2: ", type(gc.get_referrers(hangul)))
    
    
    del hangul
    gc.collect()
    print("Memory use for the first segment of factorization is:")
    monitor_memory_usage()
    
    # print("refs: ", sys.getrefcount(result))
    # print("refs: ", gc.get_referrers(result))
    
    #print(summary_parameters)
    
    # import summary_generation
    
    
    # LONG vERSION
    # agg_summary_input = summary_generation.combine_all_metadata_into_input(*summary_parameters)
    
    # result["document_summary"] = summary_generation.recursive_summarize(agg_summary_input)
    
    ##### SHOTR VRESOIN
    # generated_summary = summary_generation.summarize(*summary_parameters)
    # result["document_summary"] = generated_summary
    ###
    
    # del summary_generation
    # gc.collect()
    
    #result= {"f":3, "y":4}
    print("final memory usage:")
    monitor_memory_usage()
    return result



@app.post(SUMMARY_GENERATION_PATH)
def summary_second():
    
    summary_parameters_dic = request.get_json()
    
    summary_parameters = (summary_parameters_dic["ranked_sentences"], summary_parameters_dic["themes_detected"], summary_parameters_dic["top_locations"], summary_parameters_dic["_detected_disasters"])
    
    import summary_generation
    
    
    agg_summary_input = summary_generation.combine_all_metadata_into_input(*summary_parameters)
    
    generated_summary = summary_generation.recursive_summarize(agg_summary_input)
    
    
    del summary_generation
    gc.collect()
    
    print("summary memory usage:")
    monitor_memory_usage()
    
    return generated_summary
