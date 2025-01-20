# @Author- Sidra Effendi

# there is metadata that I want to to be visible and then there is metadata that I want for internal work so I have to
# figure that out

# This file contains code related to metadata extraction

import datetime


def get_key_val(key, pdf_metadata):
    ''' return value of the key from the dict else raise error

            @type key: string
            @param key: name of the key we want value of 
            @type pdf_metadata: dict
            @param pdf_metadata: the dict we want to extract key value from
            @rtype: string
            @return: the value of key from the dict if found else error is raised
    '''
    # check if the key exists in the dict
    key_exists = check_key_exists(key, pdf_metadata)
    if key_exists:
        return pdf_metadata[key]
    else:
        raise ValueError


def check_key_exists(key_to_check, pdf_metadata):
    ''' returns True if the key already exists in the dict else return False

            @type key_to_check: string
            @param key_to_check: the key name we want to check, if exists in the dict  
            @type pdf_metadata: dict
            @param pdf_metadata: the dict to check for existence of key
            @rtype: boolean
            @return: True if the key is present in the dict else False
    '''

    # check if key exists in dict
    if key_to_check in pdf_metadata:
        return True

    return False


def get_val_for_any_in_key_list(list_of_key_names, pdf_metadata):
    ''' Given a list of key names, whichever key is encountered first its value is returned.
            Useful in extracting information which is stored under different key names.

            @type list_of_key_names: list of strings
            @param list_of_key_names: The key names we want the value of any one of them
            @type pdf_metadata: dict
            @param pdf_metadata: the information/metadata Apache tika extracted about the document
            @rtype: NoneType or string
            @return: the value of any one key name from the pdf_metadata if found else None
    '''

    key_value = None  # default
    # check if the any of the keys is in the dict
    for key_name in list_of_key_names:
        if check_key_exists(key_name, pdf_metadata):
            key_value = get_key_val(key_name, pdf_metadata)
            break  # we found a value and don't need to look for other key values

    return key_value


def change_date_format(str_date, new_format="%Y-%m-%d"):

    """
    Convert a date string from one format to another.

    This function takes a date string in the format "%Y-%m-%dT%H:%M:%SZ" and 
    converts it to a specified new format. If the conversion fails, the function 
    returns None.

    Parameters:
    str_date (str): The date string to be converted, expected in the format "%Y-%m-%dT%H:%M:%SZ".
    new_format (str): The desired output format for the date string (default is "%Y-%m-%d").

    Returns:
    (str) or (None): The date string converted to the new format, or None if the conversion fails.
    """
    
    # given a date format it converts it to another format which can be specified
    try:
        return datetime.datetime.strptime(str_date, "%Y-%m-%dT%H:%M:%SZ").strftime(new_format)
    except:
        return None


def extract_metadata(pdf_metadata, filename:str, debug=True):
    
    """
    Extract and organize metadata from a PDF document.

    This function processes metadata extracted by Tika from a PDF document and 
    organizes it into a structured dictionary. It retrieves essential metadata 
    such as the number of pages, file name, author, document type, and creation, 
    modification, and save dates. It employs helper functions to search for 
    values associated with various possible keys and formats the extracted dates.

    Parameters:
    pdf_metadata (dict): A dictionary containing metadata extracted by Tika from the PDF document.
    filename (str): The name of the file, used to populate the file name in the final metadata dictionary.
    debug (bool): A flag to indicate whether debug information should be handled (default is True).

    Returns:
    (dict): A dictionary containing the organized metadata, which includes:
        - 'No.of Pages': The number of pages in the document.
        - 'File name': The name of the file.
        - 'charsPerPage': A representation of characters per page.
        - 'Author': The name of the document's author.
        - 'doc_type': The type of the document.
        - 'doc_created_date': The formatted creation date of the document.
        - 'doc_saved_date': The formatted save date of the document.
        - 'doc_modified_date': The formatted modification date of the document.
        - 'doc_title': The title of the document.
    """
    
    metadata_final = {}

    # the information Tika always extracts from the document and are non-negotiable
    metadata_final['No.of Pages'] = get_key_val('xmpTPg:NPages', pdf_metadata)
    metadata_final['File name'] = filename.replace(".pdf'", "")  # create contenders for titles
    metadata_final['charsPerPage'] = get_key_val(
        'pdf:charsPerPage', pdf_metadata)

    # get author name if extracted by tika, Information in the dict is repeated under different key names.
    author_list = ['Author', 'meta:author',
                   'pdf:docinfo:creator', 'dc:creator']
    author_name = get_val_for_any_in_key_list(author_list, pdf_metadata)
    metadata_final['Author'] = author_name

    # get doc type if extracted by tika
    doc_type_list = ['title', 'dc:title', 'pdf:docinfo:title']
    doc_type = get_val_for_any_in_key_list(doc_type_list, pdf_metadata)
    # returns 'Report' as doc_type maninly, might be discarded in future
    metadata_final['doc_type'] = doc_type

    # get the dates for document creation
    creation_date_list = ['Creation-Date', 'meta:creation-date',
                          'pdf:docinfo:created', 'created', 'dcterms:created']
    doc_created_date = get_val_for_any_in_key_list(
        creation_date_list, pdf_metadata)
    metadata_final['doc_created_date'] = change_date_format(doc_created_date)

    # get the dates when document was saved
    saved_date_list = ['Last-Save-Date', 'meta:save-date']
    doc_saved_date = get_val_for_any_in_key_list(saved_date_list, pdf_metadata)
    metadata_final['doc_saved_date'] = change_date_format(doc_saved_date)

    # get the dates for document modification
    modified_date_list = ['Last-Modified', 'modified', 'dcterms:modified']
    doc_modified_date = get_val_for_any_in_key_list(
        modified_date_list, pdf_metadata)
    metadata_final['doc_modified_date'] = change_date_format(doc_modified_date)

    # get doc title if extracted by tika,
    doc_title_list = ['Subject', 'meta:keyword',
                      'pdf:docinfo:keywords', 'dc:subject']
    doc_title = get_val_for_any_in_key_list(doc_title_list, pdf_metadata)
    metadata_final['doc_title'] = doc_title

    return metadata_final


def metadata_to_show():
    pass
