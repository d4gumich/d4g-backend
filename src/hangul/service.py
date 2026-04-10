import gc
import re
from pathlib import Path
from typing import Any

import fitz
import pandas as pd

from src.core.settings import settings
from src.shared import (
    clean_text,
    get_file_metadata,
    html_to_markdown,
    langcode_to_name,
    new_disaster_detection,
    summary_generation,
    theme_detection,
    title_detection,
)
from src.shared.disaster_detection import get_disasters
from src.shared.keyword_detection import generate_keywords

# Import from shared
from src.shared.location_detection import detected_potential_countries
from src.shared.report_type import detect_report_type

# Initialize spacy
_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        from spacy.language import Language
        from spacy_langdetect import LanguageDetector

        _nlp = spacy.load("en_core_web_sm")

        @Language.factory("language_detector")
        def get_lang_detector(nlp, name):
            return LanguageDetector()

        if "language_detector" not in _nlp.pipe_names:
            _nlp.add_pipe("language_detector", last=True)
    return _nlp


def detect_language(content: str) -> dict[str, Any]:
    nlp = get_nlp()
    doc = nlp(content)
    detected = doc._.language
    lang_code = detected["language"]
    detected["language"] = langcode_to_name.get_lang_name(lang_code)
    return detected


def convert_date(date: str) -> str | None:
    try:
        return pd.to_datetime(date[2:10], format="%Y%m%d").strftime("%Y-%m-%d")
    except Exception:
        return None


def get_content_pages(xml: str) -> list[str]:
    from bs4 import BeautifulSoup

    xmlTree = BeautifulSoup(xml, "lxml")
    pages = []
    for content in xmlTree.find_all("div", attrs={"class": "page"}):
        text = content.get_text()
        text = re.sub(
            r"(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)",
            " ",
            text,
        ).strip()
        text = re.sub("(\u2018|\u2019|\u201c|\u201d|\u2013|\u2020|\u2022)", "'", text)
        text = re.sub(r"\n", " ", text)
        pages.append(text)
    return pages


def get_doc_title(first_three_pages: list[str], metadata: dict[str, Any]) -> str:
    char_per_page_list = list(map(int, metadata["charsPerPage"][:3]))
    mi = min(char_per_page_list)
    indexes = [index for index in range(len(char_per_page_list)) if char_per_page_list[index] == mi]
    return first_three_pages[indexes[0]]


def get_doc_summary(first_six_pages: list[str]) -> str | None:
    for page in first_six_pages:
        if "summary" in page.lower():
            return page
    return None


def detect_v1(file_content: bytes, filename: str, kw_num: int) -> dict[str, Any]:
    import tika
    from tika import parser

    tika.initVM()

    parsed_pdf = parser.from_buffer(file_content, xmlContent=True)
    metadata = get_file_metadata.extract_metadata(parsed_pdf["metadata"], filename)
    xml_content = parsed_pdf["content"]

    content_as_pages = get_content_pages(xml_content)
    if len(content_as_pages) < 6:
        doc_title = get_doc_title(content_as_pages, metadata)
        doc_summary_text = get_doc_summary(content_as_pages)
    else:
        doc_title = get_doc_title(content_as_pages[:3], metadata)
        doc_summary_text = get_doc_summary(content_as_pages[:6])

    cleaned_content = "".join(content_as_pages)
    markdown_text = html_to_markdown.get_markdown(xml_content)

    locations = detected_potential_countries(cleaned_content)
    disasters = get_disasters(cleaned_content)
    doc_language = detect_language(cleaned_content)
    doc_report_type = detect_report_type(doc_title)

    display_content = content_as_pages[:4] if len(content_as_pages) >= 4 else content_as_pages

    return {
        "metadata": metadata,
        "document_language": doc_language,
        "document_title": doc_title,
        "document_summary": doc_summary_text,
        "content": display_content,
        "report_type": doc_report_type,
        "locations": locations,
        "disasters": disasters,
        "full_content": cleaned_content,
        "keywords": generate_keywords(doc_summary_text or "", kw_num),
        "markdown_text": markdown_text,
    }


# Base directory for the project
BASE_DIR = Path(__file__).parent.parent.parent


def detect_v2(file_content: bytes, kw_num: int, api_key: str | None, instruct_dict: dict[str, Any]) -> dict[str, Any]:
    # Ensure all instruction flags exist
    data_to_extract = [
        "Return_ALL",
        "document_language",
        "document_title",
        "document_summary",
        "content",
        "report_type",
        "locations",
        "full_content",
        "keywords",
        "markdown_text",
        "document_theme",
        "new_detected_disasters",
        "Author",
        "doc_created_date",
        "doc_modified_date",
        "num_of_pages",
        "charsPerPage",
    ]

    for key in data_to_extract:
        if key not in instruct_dict:
            instruct_dict[key] = True if key != "Return_ALL" else False
        # Convert string booleans if necessary
        elif isinstance(instruct_dict[key], str):
            instruct_dict[key] = instruct_dict[key].lower() == "true"

    if instruct_dict.get("Return_ALL"):
        for key in data_to_extract:
            instruct_dict[key] = True

    # Open PDF with FITZ
    pdf = fitz.open(stream=file_content, filetype="pdf")

    # Metadata extraction
    chars_per_page = []
    for page in pdf:
        chars_per_page.append(len(page.get_text()))

    metadata = pdf.metadata
    metadata["charsPerPage"] = chars_per_page
    metadata["No.of Pages"] = pdf.page_count
    metadata["Author"] = metadata.get("author")
    metadata["doc_created_date"] = convert_date(metadata.get("creationDate", ""))
    metadata["doc_modified_date"] = convert_date(metadata.get("modDate", ""))

    # Title extraction
    titles_list, page1_text = title_detection.print_titles(pdf[0])
    doc_title = titles_list if instruct_dict["document_title"] else None

    content_as_pages = [page.get_text("text") for page in pdf]
    doc_summary_text = get_doc_summary(content_as_pages[:6] if len(content_as_pages) >= 6 else content_as_pages)
    cleaned_content = "".join(content_as_pages)

    markdown_text = html_to_markdown.fitz_to_markdown(pdf) if instruct_dict["markdown_text"] else None
    locations = detected_potential_countries(cleaned_content) if instruct_dict["locations"] else None
    doc_language = detect_language(cleaned_content) if instruct_dict["document_language"] else None
    doc_report_type = detect_report_type(page1_text) if instruct_dict["report_type"] else None

    display_content = (
        (content_as_pages[:4] if len(content_as_pages) >= 4 else content_as_pages) if instruct_dict["content"] else None
    )

    themes_detected = None
    if instruct_dict["document_theme"]:
        themes_detected = theme_detection.detect_theme(
            cleaned_content,
            str(BASE_DIR / settings.THEME_MODEL_PATH),
            str(BASE_DIR / settings.THEME_VECTORIZER_PATH),
            theme_detection.themes_list(),
        )

    new_disasters = None
    if instruct_dict["new_detected_disasters"]:
        new_disasters = new_disaster_detection.disaster_prediction(
            cleaned_content,
            str(BASE_DIR / settings.DISASTER_VECTORIZER_PATH),
            str(BASE_DIR / settings.DISASTER_MODEL_PATH),
        )

    generated_summary = None
    if instruct_dict["document_summary"]:
        cleaned_for_summary = clean_text.clean_text(cleaned_content)
        generated_summary = summary_generation.make_summary_with_API(cleaned_for_summary, api_key)

    pdf.close()
    gc.collect()

    return {
        "metadata": metadata,
        "document_language": doc_language,
        "document_title": doc_title,
        "document_summary": generated_summary,
        "content": display_content,
        "report_type": doc_report_type,
        "locations": locations,
        "full_content": cleaned_content if instruct_dict["full_content"] else None,
        "markdown_text": markdown_text,
        "document_theme": themes_detected,
        "new_detected_disasters": new_disasters,
        "keywords": generate_keywords(generated_summary or "", kw_num),
    }
