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


paths = retrieve_report_paths("D:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021")
