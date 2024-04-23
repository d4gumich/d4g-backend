from flask import Flask, request
from flask_cors import CORS
from chetah_v1 import search
from hangul import detect_second_version #detect
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
HANGUL_PATH = f'{BASE_PATH}/hangul'
HANGUL_SECOND_VERSION_PATH = f'{BASE_PATH_SECOND_VERSION}/hangul'


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
    monitor_memory_usage()
    result = detect_second_version(file, kw_num)
    #result= {"f":3, "y":4}
    monitor_memory_usage()
    return result
