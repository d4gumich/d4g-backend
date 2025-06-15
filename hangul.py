# @author- SIdra Effendi

import spacy
import re
from spacy_langdetect import LanguageDetector
from spacy.language import Language
from fastapi import UploadFile
from bs4 import BeautifulSoup
import gc
from io import BytesIO
from werkzeug.datastructures import FileStorage
import fitz
import pandas as pd


from location_detection import detected_potential_countries
from disaster_detection import get_disasters
from report_type import detect_report_type
from keyword_detection import generate_keywords
import get_file_metadata
import langcode_to_name 
import html_to_markdown
import theme_detection
import CleanText
import new_disaster_detection
import title_detection
import summary_generation




nlp = spacy.load('en_core_web_sm')

def get_content_pages(xml):
    
    """
    GET XML and return clean text data
    """
    
    xmlTree = BeautifulSoup(xml, 'lxml')
    pages = []
    for _, content in enumerate(xmlTree.find_all('div', attrs={'class': 'page'})):
        text = content.get_text()
        text = re.sub(r'(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)', ' ', text).strip()
        text = re.sub(u"(\u2018|\u2019|\u201c|\u201d|\u2013|\u2020|\u2022)", "'", text)
        text = re.sub(r'\n',' ', text)
        pages.append(text)
        
    return pages
        

def get_doc_title(first_three_pages, metadata):

    char_per_page_list = list(map(int, metadata['charsPerPage'][:3]))
    mi = min(char_per_page_list)
    indexes = [index for index in range(
        len(char_per_page_list)) if char_per_page_list[index] == mi]

    return first_three_pages[indexes[0]]


def get_doc_summary(first_six_pages):
    check_str = 'summary'
    summary = None
    for page_content in first_six_pages:
        if check_str in page_content.lower():
            summary = page_content
    return summary


def clean_doc_content(content):
    return content.replace("\n", "")


def convert_date (date):
    
    """
    Converts a substring of the input string into a formatted date.

    - Extracts characters from index 2 to 10, assuming they represent 'YYYYMMDD'.
    - Converts the extracted value to a date using Pandas.
    - Returns the formatted date string ('YYYY-MM-DD').
    - If the input is invalid, returns None.

    Args:
        date (str): A string containing a date at index 2-10.

    Returns:
        str or None: The formatted date ('YYYY-MM-DD') or None if conversion fails.
    """
    
    try:
        return pd.to_datetime(date[2:10], format='%Y%m%d').strftime('%Y-%m-%d')

    except:
        return None
    

def extract_pdf_data(files, want_metadata=False, want_content=False):
    '''Given a list of path to PDFs, iterate over the list,
     and for each string, read in the PDF form its path and 
     return extracted text.

     The flags might be changed during further development. 
     Right now they are designed to help in the process of 
     development and debugging.
     Developing what details about the document we want to 
     look at closely - metadata or content or both.
     It also returns content as pages so that we can decide 
     which pages to target going forward for information.

     @type list_of_path_to_pdf: list of string - [str1, str2]
     @param list_of_path_to_pdf: path of the pdf file to be read
     @type want_metadata: boolean
     @param want_metadata: Gets metadata about a document - default value True
     @type want_content: boolean
     @param want_content: Gets all the content of the document - default value False
     @type content_as_pages: boolean
     @param content_as_pages: Gets the content of the documents as pages else as a single text blob- default value True
     @rtype: List of dictionaries - [{metadata:'', 'content: ''}, {metadata:'', 'content: ''}, {metadata:'', 'content: ''}]
     @return:  For each document we get its metadata or content or both

    '''
    import tika
    from tika import parser
    
    
    tika.initVM()
    data_of_pdfs = []
    for file in files:
        pdf = {}
        parsed_pdf = parser.from_buffer(file.read() , xmlContent=True)

        if want_metadata:
            

            extracted_pdf_metadata = get_file_metadata.extract_metadata(
                parsed_pdf["metadata"], file.name)

            
            pdf['metadata'] = extracted_pdf_metadata

        if want_content:
            pdf['xml_content'] = parsed_pdf['content']

        data_of_pdfs.append(pdf)
        
    return data_of_pdfs

    
    
    
@Language.factory("language_detector")
def get_lang_detector(nlp, name):
    return LanguageDetector()


def detect_language(content):
    doc = nlp(content)
    detected = doc._.language
    lang_code_detected = (detected['language'])
    
    detected['language'] = langcode_to_name.get_lang_name(lang_code_detected) # map language code to language name
    
    return detected #doc._.language


def copy_file_storage(original_fs):
    # Read the content of the original FileStorage object
    original_fs.stream.seek(0)  # Go to the start of the file
    file_content = original_fs.stream.read()
    
    # Create a BytesIO object with the file content
    file_stream = BytesIO(file_content)
    
    # Create a new FileStorage object with the BytesIO stream
    copied_fs = FileStorage(stream=file_stream, filename=original_fs.filename, content_type=original_fs.content_type)
    
    return copied_fs



nlp.add_pipe('language_detector', last=True)



# -------------------- HANGUL 1.0 --------------------

def detect(file: UploadFile, kw_num: int):
    
    
    metadata_of_pdfs = extract_pdf_data(
        [file], want_metadata=True, want_content=True)
    # This is what was used throughout the document
    content_as_pages = get_content_pages(metadata_of_pdfs[0]['xml_content'])
    if len(content_as_pages) < 6:
        doc_title = get_doc_title(
            content_as_pages, metadata_of_pdfs[0]['metadata'])
        doc_summary = get_doc_summary(content_as_pages)
    else:
        doc_title = get_doc_title(
            content_as_pages[:3], metadata_of_pdfs[0]['metadata'])
        doc_summary = get_doc_summary(content_as_pages[:6])
        
    cleaned_content = ''.join(content_as_pages)
    markdown_text = html_to_markdown.get_markdown(metadata_of_pdfs[0]['xml_content'])

    locations = detected_potential_countries(cleaned_content)
    disasters = get_disasters(cleaned_content)
    doc_language = detect_language(cleaned_content)
    doc_report_type = detect_report_type(doc_title)
    if len(content_as_pages) < 4:
        display_content = content_as_pages
    else:
        display_content = content_as_pages[:4]

    return {
        'metadata': metadata_of_pdfs[0]['metadata'],
        'document_language': doc_language,
        'document_title': doc_title,
        'document_summary': doc_summary,
        'content': display_content,
        'report_type': doc_report_type,
        'locations': locations,
        'disasters': disasters,
        'full_content': cleaned_content,
        'keywords': generate_keywords(doc_summary, kw_num),
        'markdown_text': markdown_text
    }



# -------------------- HANGUL 2.0 --------------------

def detect_second_version(file: UploadFile, kw_num: int, API_key, instruct_dict: dict):
    """
    instruct_dict @dict: a dictionary that indicates which parameters does the user want
    """
    
    # di = {
    #     'metadata': metadata_of_pdfs[0]['metadata'],
    #     'document_language': doc_language,
    #     'document_title': doc_title,
    #     'document_summary_parameters': summary_generation_parameters, #generated_summary,
    #     'content': display_content,
    #     'report_type': doc_report_type,
    #     'locations': locations,
    #     'full_content': cleaned_content,
    #     'keywords': generate_keywords(doc_summary, kw_num),
    #     'markdown_text': markdown_text,
    #     'document_theme': themes_detected,
    #     'new_detected_disasters': new_detected_disasters
    # } 
    
    
    data_to_extract = ["Return_ALL", "document_language", "document_title",
                       "document_summary", "content", "report_type",
                       "locations", "full_content", "keywords",
                       "markdown_text", "document_theme", "new_detected_disasters",
                       "Author", "doc_created_date", "doc_modified_date", "num_of_pages", "charsPerPage"]
    
    for dat in data_to_extract:
        if dat not in instruct_dict.keys():
            if dat == "Return_ALL":
                instruct_dict[dat] = False
            else:
                instruct_dict[dat] = True
            
        try:
            instruct_dict[dat] = eval(instruct_dict[dat])
        except:
            pass
        
    
    # If the user wants all, overwritte all the booleans           
    if instruct_dict["Return_ALL"]:
        for dat in data_to_extract:
            instruct_dict[dat] = True
            
    
    # for i in instruct_dict.keys():
    #     print(i, instruct_dict[i], type(instruct_dict[i]))
    
    
    
    # Open PDF with FITZ
    pdf = fitz.open(stream=file.stream.read(), filetype="pdf")
    
    
    
    chars_per_page = []
    for page_number in range(pdf.page_count):
        page = pdf[page_number]
        page_text = page.get_text()
        char_count = len(page_text)
        chars_per_page.append(char_count)
        
        
    metadata_dict = pdf.metadata
    metadata_dict["charsPerPage"] = chars_per_page
    metadata_dict["No.of Pages"] = pdf.page_count
    metadata_dict["Author"] = metadata_dict["author"]
    del metadata_dict["author"]
    
    metadata_dict["doc_created_date"] = convert_date(metadata_dict["creationDate"])
    del metadata_dict["creationDate"]
    
    metadata_dict["doc_modified_date"] = convert_date(metadata_dict["modDate"])
    del metadata_dict["modDate"]
    
    del metadata_dict["keywords"]
    del metadata_dict["subject"]
    del metadata_dict["trapped"]
    del metadata_dict["title"]


        
    # Getting the title

    titles_and_sizes_list, page1_text = title_detection.print_titles(pdf[0])
    titles_and_sizes_list = [(line[0], line[1].strip()) for line in titles_and_sizes_list]
    
    # Find the title candidate with the highest font
    # max_font_title = max(titles_and_sizes_list, key=lambda x: x[0])
    
    if instruct_dict["document_title"] == False:
        
        doc_title = None
        
    else:
        # Extract the string from that tuple
        doc_title = titles_and_sizes_list #max_font_title[1].strip()

        
    
    

    # This is what was used throughout the document
    content_as_pages = [page.get_text("text") for page in pdf]
    if len(content_as_pages) < 6:
        doc_summary = get_doc_summary(content_as_pages)
    else:
        doc_summary = get_doc_summary(content_as_pages[:6])
        
    cleaned_content = ''.join(content_as_pages)
    

    
    
    # MARKDOWN EXTRACTION
    if instruct_dict["markdown_text"] == False:
        
        markdown_text = None
        
    else:

        markdown_text = html_to_markdown.fitz_to_markdown(pdf)
        
        
    # LOCATIONS EXTRACTION
    if instruct_dict["locations"] == False:
        
        locations = None
        
    else:
        
        # Detect Locations
        locations = detected_potential_countries(cleaned_content)
        
        
        
    # LANGUAGE EXTRACTION
    if instruct_dict["document_language"] == False:
        
        doc_language = None
        
    else:
        
        # Detect Language
        doc_language = detect_language(cleaned_content)
        
        
        
    # REPORT_TYPE EXTRACTION
    if instruct_dict["report_type"] == False:
        
        doc_report_type = None
        
    else:
    
        # Detect report type
        doc_report_type = detect_report_type(page1_text)
        
        
        
    # DISPLAY_CONTENT EXTRACTION
    if instruct_dict["content"] == False:
        
        display_content = None
        
    else:
        
        if len(content_as_pages) < 4:
            display_content = content_as_pages
        else:
            display_content = content_as_pages[:4]
            
        
        
    # THEMES EXTRACTION
    if instruct_dict["document_theme"] == False:
        
        themes_detected = None
        
    else:
        
        # Detect Themes
        themes_detected = theme_detection.detect_theme(cleaned_content,'Model_RW_ThemeDetect.pkl', 
                                 'Vectorizer_RW_ThemeDetect.pkl', 
                                 theme_detection.themes_list() )


    # THEMES EXTRACTION
    if instruct_dict["new_detected_disasters"] == False:
        
        new_detected_disasters = None
        
    else:
        
        # Detect disasters
        new_detected_disasters = new_disaster_detection.disaster_prediction(cleaned_content, 'tfidf_vectorizer_disaster.pkl')

    ### Summary generation section:   
    
    # THEMES EXTRACTION
    if instruct_dict["document_summary"] == False:
        

        generated_summary = None
        
    else:

        cleaned_text_for_summary = CleanText.clean_text(cleaned_content)

        
        # generated_summary = "I GENERATED THIS AMAZING SUMMARY"
        
        
        generated_summary = summary_generation.make_summary_with_API(cleaned_text_for_summary, API_key)
        


    # Metadata selection
    if instruct_dict["Author"] == False:
        metadata_dict["Author"] = None
        
    if instruct_dict["doc_created_date"] == False:
        metadata_dict["doc_created_date"] = None
        
    if instruct_dict["doc_modified_date"] == False:
        metadata_dict["doc_modified_date"] = None
        
    if instruct_dict["num_of_pages"] == False:
        metadata_dict["No.of Pages"] = None
        
    if instruct_dict["charsPerPage"] == False:
        metadata_dict["charsPerPage"] = None
        
        
    if instruct_dict["full_content"] == False:
        cleaned_content = None
        
     
    pdf.close()
    gc.collect()
    
    return {
        'metadata': metadata_dict,
        'document_language': doc_language,
        'document_title': doc_title,
        'document_summary': generated_summary, #generated_summary,
        'content': display_content,
        'report_type': doc_report_type,
        'locations': locations,
        'full_content': cleaned_content,
        'markdown_text': markdown_text,
        'document_theme': themes_detected,
        'new_detected_disasters': new_detected_disasters,
        "keywords": generate_keywords(generated_summary, kw_num),
    }