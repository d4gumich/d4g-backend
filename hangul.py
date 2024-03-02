# @author- SIdra Effendi
import tika
from tika import parser
import spacy
import re
import html2text
from spacy_langdetect import LanguageDetector
from spacy.language import Language
from fastapi import UploadFile
from bs4 import BeautifulSoup
from io import StringIO

from disaster_detection import get_disasters
from get_file_metadata import extract_metadata
from location_detection import detected_potential_countries
from report_type import detect_report_type
from keyword_detection import generate_keywords
from langcode_to_name import get_lang_name
from html_to_markdown import get_markdown
import theme_detection
from title_extraction import extract_fontsize_title
from sentence_ranking import textrank_sentences
import summary_generation
import new_disaster_detection

tika.initVM()
nlp = spacy.load('en_core_web_md')

# def extract_pdf_content(pdf_path, content_as_pages):

#     if content_as_pages:
#         raw_xml = parser.from_file(pdf_path, xmlContent=True)
#         body = raw_xml['content'].split('<body>')[1].split('</body>')[0]
#         body_without_tag = body.replace("<p>", "").replace("</p>", "\n").replace("<div>", "").replace("</div>","\n").replace("<p />","\n")
#         text_pages = body_without_tag.split("""<div class="page">""")[1:]
#         num_pages = len(text_pages)
#         print(num_pages)
#         if num_pages==int(raw_xml['metadata']['xmpTPg:NPages']) :
#             for i in range(3):
#             # for i in range(num_pages):
#                 print('page number: '+ str(i+1))
#                 print(text_pages[i].replace("\n", ""))
#                 print('\n')
#         pdf_content = body_without_tag
#     else:
#         parsed_pdf = parser.from_file(pdf_path)
#         pdf_content= parsed_pdf["content"].replace("\n", "")
#     return pdf_content


def get_content_pages(xml):
    xmlTree = BeautifulSoup(xml, 'lxml')
    pages = []
    for _, content in enumerate(xmlTree.find_all('div', attrs={'class': 'page'})):
        text = content.get_text()
        text = re.sub(r'(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)', ' ', text).strip()
        text = re.sub(u"(\u2018|\u2019|\u201c|\u201d|\u2013|\u2020|\u2022)", "'", text)
        text = re.sub(r'\n',' ', text)
        pages.append(text)
    return pages
        
#     print(raw_xml)
#     body = raw_xml['content'].split('<body>')[1].split('</body>')[0]
#     body_without_tag = body.replace("<p>", "").replace(
#         "</p>", "\n").replace("<div>", "").replace("</div>", "\n").replace("<p />", "\n")
#     text_pages = body_without_tag.split("""<div class="page">""")[1:]
#     num_pages = len(text_pages)
#     pages_content = []
#     if num_pages == int(raw_xml['metadata']['xmpTPg:NPages']):
#         # for i in range(5):
#         for i in range(num_pages):
#             #         # print('page number: '+ str(i+1))
#             h = html2text.HTML2Text()
#             h.ignore_links = True
#             # h.escape_all = True
#             text_pages[i] = h.handle(text_pages[i].replace("\n", " "))
#             text_pages[i] = re.sub(
#                 r'\s*(?:https?://)?www\.\S*\.[A-Za-z]{2,5}\s*', ' ', text_pages[i].replace("\n", " ")).strip()
#             text_pages[i] = re.sub(
#                 u"(\u2018|\u2019|\u201c|\u201d|\u2013|\u2020|\u2022)", "'", text_pages[i])
#             pages_content.append(text_pages[i])
#         pdf_content = pages_content
#     return pdf_content


def get_doc_title(first_three_pages, metadata):

    char_per_page_list = list(map(int, metadata['charsPerPage'][:3]))
    mi = min(char_per_page_list)
    indexes = [index for index in range(
        len(char_per_page_list)) if char_per_page_list[index] == mi]

    return first_three_pages[indexes[0]]


def get_doc_summary(first_six_pages):
    # char_per_page_list = list(map(int, metadata['charsPerPage'][:6]))
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
            extracted_pdf_metadata = extract_metadata(
                parsed_pdf["metadata"], file.name)
            pdf['metadata'] = extracted_pdf_metadata

        if want_content:
            pdf['xml_content'] = parsed_pdf['content']

        data_of_pdfs.append(pdf)

    return data_of_pdfs


# def extract_pdf_data(file_paths, want_metadata=True, want_content=False, content_as_pages=True):
#     '''Given a list of path to PDFs, iterate over the list,
#      and for each string, read in the PDF form its path and
#      return extracted text.

#      The flags might be changed during further development.
#      Right now they are designed to help in the process of
#      development and debugging.
#      Developing what details about the document we want to
#      look at closely - metadata or content or both.
#      It also returns content as pages so that we can decide
#      which pages to target going forward for information.

#      @type list_of_path_to_pdf: list of string - [str1, str2]
#      @param list_of_path_to_pdf: path of the pdf file to be read
#      @type want_metadata: boolean
#      @param want_metadata: Gets metadata about a document - default value True
#      @type want_content: boolean
#      @param want_content: Gets all the content of the document - default value False
#      @type content_as_pages: boolean
#      @param content_as_pages: Gets the content of the documents as pages else as a single text blob- default value True
#      @rtype: List of dictionaries - [{metadata:'', 'content: ''}, {metadata:'', 'content: ''}, {metadata:'', 'content: ''}]
#      @return:  For each document we get its metadata or content or both

#     '''
#     data_of_pdfs = []
#     for file_path in file_paths:
#         pdf = {}
#         parsed_pdf = parser.from_file(file_path)

#         if want_metadata:
#             extracted_pdf_metadata = extract_metadata(parsed_pdf["metadata"])
#             pdf['metadata'] = extracted_pdf_metadata

#         if want_content:
#             extracted_pdf_content = extract_pdf_content(
#                 file_path, content_as_pages)
#             pdf['content'] = extracted_pdf_content

#         data_of_pdfs.append(pdf)

#     return data_of_pdfs

    # return metadata,results
@Language.factory("language_detector")
def get_lang_detector(nlp, name):
    return LanguageDetector()


def detect_language(content):
    doc = nlp(content)
    detected = doc._.language
    lang_code_detected = (detected['language'])
    detected['language'] = get_lang_name(lang_code_detected) # map language code to language name

    return detected #doc._.language






nlp.add_pipe('language_detector', last=True)


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


def detect_second_version(file: UploadFile, kw_num: int):
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
    themes_detected = theme_detection.detect_theme(cleaned_content,'Model_RW_ThemeDetect.pkl', 
                             'Vectorizer_RW_ThemeDetect.pkl', 
                             theme_detection.themes_list() )
    title = extract_fontsize_title(file, title_character_size = 13)

    new_detected_disasters = new_disaster_detection.disaster_prediction(cleaned_content, 'tfidf_vectorizer_disaster.pkl')
    ### Summary generation section:
    ranked_sentences_input = textrank_sentences(cleaned_content, sentence_lim=10)
    locations_names_occs = list(locations.values())
    
    if len(locations_names_occs) <= 5:
        top_locations = locations_names_occs
    else:
        sorted_locations_names_occs = sorted(locations_names_occs, key=lambda x: x['no_of_occurences'], reverse=True)
        top_locations = [d['name'] for d in sorted_locations_names_occs[:5]]
    
    agg_summary_input = summary_generation.combine_all_metadata_into_input(ranked_sentences_input,
                                                                           themes_detected,
                                                                           top_locations,
                                                                           new_detected_disasters
                                                                           )
    
    generated_summary = summary_generation.recursive_summarize(agg_summary_input)
    ###
    
    
    return {
        'metadata': metadata_of_pdfs[0]['metadata'],
        'document_language': doc_language,
        'document_title': doc_title,
        'document_summary': generated_summary,
        'content': display_content,
        'report_type': doc_report_type,
        'locations': locations,
        'disasters': disasters,
        'full_content': cleaned_content,
        'keywords': generate_keywords(doc_summary, kw_num),
        'markdown_text': markdown_text,
        'document_theme': themes_detected,
        'document_title': title,
        'new_detected_disasters': new_detected_disasters
    }