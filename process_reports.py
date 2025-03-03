from pathlib import Path
import requests
import json
import re
import chetah_utils

HANGUL_API_URL = 'https://d4gumsi.pythonanywhere.com/api/v2/products/hangul'
PAYLOAD = {"kw_num":"5","Return_ALL":True}
PATHS_DIR = "E:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021"
OUT_DIRECTORY = "E:/process_output"

paths = chetah_utils.retrieve_report_paths(PATHS_DIR)
# Define the output location for the JSON files
out_directory = Path(OUT_DIRECTORY)
# Double check, if not create the directory
out_directory.mkdir(parents=True,exist_ok=True)
id=0
total_paths = len(paths)
for path in paths:
    print(f"{(id+1)/total_paths}")
    try:
        result_dict = chetah_utils.process_pdf_path(path,HANGUL_API_URL,PAYLOAD)
        result_dict['Chetah_Data'] = {}
        result_dict['Chetah_Data']['organization'] = chetah_utils.find_organization(path)
        result_dict['Chetah_Data']['year_of_report'] = chetah_utils.detect_year_of_report(path.name)
        result_dict['Chetah_Data']['filename'] = path.name
    except Exception as e:
        # Take note of the error, and file name
        result_dict = {}
        result_dict['Path'] = str(path)
        result_dict['Error'] = str(e)
    result_name = out_directory / f"res-{id}.json"
    with open(result_name, "w",encoding='utf-8') as json_file:
        json.dump(result_dict, json_file)
    id = id+1
