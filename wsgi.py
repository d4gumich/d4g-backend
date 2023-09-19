from flask import Flask, request
from chetah_v1 import search
from hangul import detect

app = Flask(__name__)

BASE_PATH = '/api/v1/products'
CHETAH_PATH = f'{BASE_PATH}/chetah'
HANGUL_PATH = f'{BASE_PATH}/hangul'


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
