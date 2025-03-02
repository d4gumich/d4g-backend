from pathlib import Path
import requests
import json

HANGUL_API_URL = 'https://d4gumsi.pythonanywhere.com/api/v2/products/hangul'
PAYLOAD = {"kw_num":"5","Return_ALL":True}
PATHS_DIR = "E:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021"

def retrieve_report_paths(root_folder):
    # This function will return a list of all file paths of pdf reports
    # matching the conditions of being a PDF and located within
    # a "clean_eng_docs" sub-directory

    # Convert the string path, to a path object
    root_folder = Path(root_folder)

    # Retrieve all Report PDF's from 'clean_eng_docs' directories
    files = list(root_folder.glob("**/clean_eng_docs/*.pdf"))

    # We'll return as path objects, converting to a csv can wait.
    # files = [str(file) for file in files]

    return files

def process_pdf_path(report_path: Path):
    # This function utilizes the constants to make a call to Hangul
    with report_path.open("rb") as f:
        files = {"file":(report_path.name,f)}
        response = requests.post(HANGUL_API_URL, files=files, data=PAYLOAD)
    return response.json()

paths = retrieve_report_paths(PATHS_DIR)
# Define the output location for the JSON files
out_directory = Path("E:/process_output")
# Double check, if not create the directory
out_directory.mkdir(parents=True,exist_ok=True)
id=0
for path in paths:
    try:
        result_dict = process_pdf_path(path)
    except Exception as e:
        # Take note of the error, and file name
        result_dict = {}
        result_dict['Path'] = str(path)
        result_dict['Error'] = str(e)
    result_name = out_directory / f"res-{id}.json"
    with open(result_name, "w",encoding='utf-8') as json_file:
        json.dump(result_dict, json_file)
    id = id+1
