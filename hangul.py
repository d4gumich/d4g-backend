# @author- SIdra Effendi
import tika
from tika import parser
import spacy
import re
from spacy_langdetect import LanguageDetector
from spacy.language import Language
from fastapi import UploadFile
from bs4 import BeautifulSoup
import gc
from io import BytesIO
from werkzeug.datastructures import FileStorage


from location_detection import detected_potential_countries
from disaster_detection import get_disasters
from html_to_markdown import get_markdown
from report_type import detect_report_type
from keyword_detection import generate_keywords
import get_file_metadata
import langcode_to_name 
import html_to_markdown
import theme_detection
import sentence_ranking
import new_disaster_detection
import title_detection



tika.initVM()
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
    markdown_text = get_markdown(metadata_of_pdfs[0]['xml_content'])

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

def detect_second_version(file: UploadFile, kw_num: int):
    # Extract metadata from FileStorage object
    metadata_of_pdfs = extract_pdf_data(
        [file], want_metadata=True, want_content=True)
    
    # Copy the file into a new file to be able to read the title
    # If I don't do this, after extracting metadata from the flask
    # FileStorage object, the title extraction does not work
    file2 = copy_file_storage(file)
    
    # Getting the title
    stream = file2.stream.read()
    titles_and_sizes_list, page1_text = title_detection.print_titles(stream)
    
    
    # Find the title candidate with the highest font
    max_font_title = max(titles_and_sizes_list, key=lambda x: x[0])
    # Extract the string from that tuple
    doc_title = max_font_title[1].strip()
    

    

    # This is what was used throughout the document
    content_as_pages = get_content_pages(metadata_of_pdfs[0]['xml_content'])
    if len(content_as_pages) < 6:
        doc_summary = get_doc_summary(content_as_pages)
    else:
        doc_summary = get_doc_summary(content_as_pages[:6])
        
    cleaned_content = ''.join(content_as_pages)


    markdown_text = html_to_markdown.get_markdown(metadata_of_pdfs[0]['xml_content'])

    # Detect Locations
    locations = detected_potential_countries(cleaned_content)
    

    # Detect Language
    doc_language = detect_language(cleaned_content)
    
    # Detect report type
    doc_report_type = detect_report_type(page1_text)
    
    if len(content_as_pages) < 4:
        display_content = content_as_pages
    else:
        display_content = content_as_pages[:4]
        
        
        
    # Detect Themes
    themes_detected = theme_detection.detect_theme(cleaned_content,'Model_RW_ThemeDetect.pkl', 
                             'Vectorizer_RW_ThemeDetect.pkl', 
                             theme_detection.themes_list() )



    # Detect disasters
    new_detected_disasters = new_disaster_detection.disaster_prediction(cleaned_content, 'tfidf_vectorizer_disaster.pkl')

    
    
    ### Summary generation section:

    ranked_sentences_input = sentence_ranking.textrank_sentences(cleaned_content, sentence_lim=10)

    
    locations_names_occs = list(locations.values())
    
    if len(locations_names_occs) <= 5:
        top_locations = locations_names_occs
    else:
        sorted_locations_names_occs = sorted(locations_names_occs, key=lambda x: x['no_of_occurences'], reverse=True)
        top_locations = [d['name'] for d in sorted_locations_names_occs[:5]]
        
        
    
    summary_generation_parameters = {"ranked_sentences":ranked_sentences_input,
                                     "themes_detected" : themes_detected,
                                     "top_locations" : top_locations,
                                     "_detected_disasters" : new_detected_disasters}
    
    gc.collect()
    
    return {
        'metadata': metadata_of_pdfs[0]['metadata'],
        'document_language': doc_language,
        'document_title': doc_title,
        'document_summary_parameters': summary_generation_parameters, #generated_summary,
        'content': display_content,
        'report_type': doc_report_type,
        'locations': locations,
        'full_content': cleaned_content,
        'keywords': generate_keywords(doc_summary, kw_num),
        'markdown_text': markdown_text,
        'document_theme': themes_detected,
        'new_detected_disasters': new_detected_disasters
    }