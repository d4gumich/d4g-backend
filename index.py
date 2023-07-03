from fastapi import FastAPI, Form, File, UploadFile
from typing import Annotated
from chetah_v1 import search
from hangul import detect

from models import ChetahModel

d4g = FastAPI()

BASE_PATH = '/api/v1/products'
CHETAH_PATH = f'{BASE_PATH}/chetah'
HANGUL_PATH = f'{BASE_PATH}/hangul'


@d4g.post(CHETAH_PATH)
async def chetah(body: ChetahModel):
    return search(body.query)


@d4g.post(HANGUL_PATH)
async def hangul(kw_num: Annotated[int, Form()],
                 file: Annotated[UploadFile, File(description="File uploaded to the Hangul system")]):
    return await detect(file, kw_num)
