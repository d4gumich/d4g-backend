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

from pypdf import PdfReader # Handles pdf files located at each path
def retrieve_metadata(file_path: Path):
    # Fills a verbose dictionary with metadata
    meta_dict = {}

    # Retrieves the filename
    meta_dict['filename'] = file_path.name

    # Retrieves the metadata
    num_pages = -1
    try:
        with open(file_path, 'rb') as pdf:
            reader = PdfReader(pdf)
            # Retrieves the number of pages in a PDF file, checks that the input is a path object
            meta_dict['num_of_pages'] = len(reader.pages)

            # Retrieves the author
            meta_dict['author'] = reader.metadata.author

            # Retrieves the document creation date
            meta_dict['doc_creation_date'] = reader.metadata.creation_date

            # Retrieves the document modification date
            meta_dict['doc_modification_date'] = reader.metadata.modification_date

    except Exception as e:
        print(f"exception occured with {file_path} when attempting to retrieve metadata:")
        print(f"{e}")
        meta_dict['num_of_pages'] = -1

    return meta_dict

from werkzeug.datastructures import FileStorage
from io import BytesIO

def path_to_filestorage(file_path: Path) -> FileStorage:
    # Creates a FileStorage object from a file path, handling potential exceptions
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()  #Read file contents into memory
            return FileStorage(stream=BytesIO(file_content), filename=file_path.name)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def process_pdf(file_path, want_metadata=False, want_content=False):
    """Processes a PDF file safely using context management."""
    try:
      with open(file_path, 'rb') as file_obj:
          #Use the file object directly within the context manager
          result = hangul_module.detect_second_version([file_obj],9)
          return result
    except Exception as e:
        print(f"An error occured: {e}")
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

# attempts at the first zero
file_storage_object = path_to_filestorage(paths[0])
print(file_storage_object.stream)
print(f"FileStorage stream size: {len(file_storage_object.stream.read())}")
print(file_storage_object.name)
# Attempt second version
result = hangul_module.detect_second_version(file_storage_object,9)
print(result)