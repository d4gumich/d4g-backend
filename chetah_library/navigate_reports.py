from pathlib import Path
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

from tika import parser
def retrieve_metadata(file_path: Path):

    # Retrieves the metadata
    try:
            # First parse the file with Tika
            parsed_report = parser.from_file(str(file_path))

            # Metadata parse
            meta_data = parsed_report.get('metadata', {}) # the {}, means if it fails to retrieve, it gives an empty dictionary

    except Exception as e:
        print(f"exception occured with {file_path} when attempting to retrieve metadata:")
        print(f"{e}")

    return meta_data

from werkzeug.datastructures import FileStorage
from io import BytesIO

def path_to_filestorage(file_path: Path, meta_dict) -> FileStorage:
    # Creates a FileStorage object from a file path, handling potential exceptions
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()  #Read file contents into memory
            print(f"This is the file_path.name in the conversion function{file_path.name}")
            return FileStorage(stream=BytesIO(file_content), filename=file_path.name,name=file_path.name,headers=meta_dict)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Pathlib is already part of this file, so define the hangul import statement
import importlib.util # needed from the standard library to load dynamically
import sys

def load_parent_file(parent_file_name):
    # The objective of this function is to dynamically load other python files from the parent directory
    # and make their functions available here
    # Takes file name and returns the reference to the loaded module
    file_path = Path(__file__).parent.parent.resolve() / parent_file_name
    sys.path.insert(0,str(file_path.parent))
    module_name = file_path.stem
    # create a module specification, loads modules that are not standard search paths
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def process_pdf_path(report_path: Path):
    # This function takes a single path and calls the required hangul functions
    # Retrieve metadata
    meta_data = retrieve_metadata(report_path)
    file_storage_object = path_to_filestorage(report_path,meta_dict=meta_data)
    # Attempt second version
    result = hangul_mod.detect_second_version(file_storage_object,5)
    # Check
    summary_parameters = (result['document_summary_parameters']["ranked_sentences"],
                          result['document_summary_parameters']["themes_detected"],
                          result['document_summary_parameters']["top_locations"],
                          result['document_summary_parameters']["_detected_disasters"],)
    agg_summary_input = summary_module.combine_all_metadata_into_input(*summary_parameters)
    generated_summary = summary_module.recursive_summarize(agg_summary_input)
    # Take the necessary info to the generated overall result
    result['generated_summary'] = generated_summary
    return result

# Import the hangul libraries to utilize their functions, such as hangul and summary generation
hangul_mod = load_parent_file("hangul.py")
summary_module = load_parent_file("summary_generation.py")
paths = retrieve_report_paths("E:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021")

# Loop through each report, exporting a json file for each
import json
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
    with open(result_name, "w") as json_file:
        json.dump(result_dict, json_file)
    id = id+1

