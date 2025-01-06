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
# I need the parent of the parent of the current file, and to resolve into an absolute path
file_path = Path(__file__).parent.parent.resolve() / "hangul.py"
sys.path.insert(0,str(file_path.parent))
module_name = file_path.stem
# create a module specification, loads modules that are not standard search paths
spec = importlib.util.spec_from_file_location(module_name, file_path)
hangul_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hangul_module)

paths = retrieve_report_paths("E:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021")

# attempts the first report
# Retrieve metadata
meta_data = retrieve_metadata(paths[0])
#print(meta_data)
file_storage_object = path_to_filestorage(paths[0],meta_dict=meta_data)

# Attempt second version
result = hangul_module.detect_second_version(file_storage_object,5)

# Get the automatic summary generation, first import the library
file_path = Path(__file__).parent.parent.resolve() / "summary_generation.py"
sys.path.insert(0,str(file_path.parent))
module_name = file_path.stem
# create a module specification, loads modules that are not standard search paths
spec = importlib.util.spec_from_file_location(module_name, file_path)
summary_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary_module)

summary_parameters = (result['document_summary_parameters']["ranked_sentences"],
                      result['document_summary_parameters']["themes_detected"],
                      result['document_summary_parameters']["top_locations"],
                      result['document_summary_parameters']["_detected_disasters"],)
agg_summary_input = summary_module.combine_all_metadata_into_input(*summary_parameters)
generated_summary = summary_module.recursive_summarize(agg_summary_input)
print(generated_summary)
import json
with open("test.json", "w") as json_file:
    json.dump(result, json_file)
