from flask import Flask, request
from flask_cors import CORS
from chetah_v1 import search
from hangul import detect, detect_second_version

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


@app.post(HANGUL_PATH)
def hangul():
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    return detect(file, kw_num)

#endpoint for hangul 2.0
@app.post(HANGUL_SECOND_VERSION_PATH)
def hangul_second():
    file = request.files['file']
    kw_num = int(request.form['kw_num'])
    return detect_second_version(file, kw_num)
