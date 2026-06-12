import gc
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from src.core.settings import settings
from src.shared import (
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


def convert_date(date_str: str) -> str:
    if not date_str:
        return ""
    import pandas as pd

    try:
        # Standard PDF date format: D:YYYYMMDDHHMMSS...
        clean_date = date_str
        if clean_date.startswith("D:"):
            clean_date = clean_date[2:10]
        else:
            # Try to grab first 8 digits
            digits = re.findall(r"\d+", clean_date)
            if digits and len(digits[0]) >= 8:
                clean_date = digits[0][:8]
            elif digits and len(digits[0]) == 4:
                # Just a year
                return f"{digits[0]}-01-01"

        return pd.to_datetime(clean_date, format="%Y%m%d").strftime("%Y-%m-%d")
    except Exception:
        # Try generic parser as last resort
        try:
            return pd.to_datetime(date_str).strftime("%Y-%m-%d")
        except Exception:
            return date_str


def extract_metadata_with_llm(text: str, api_key: str | None, model_name: str | None) -> dict[str, Any]:
    """Uses LLM to extract Author and Publication Date from the first page text."""
    import google.generativeai as genai

    try:
        # Get the key
        key = api_key or settings.GOOGLE_API_KEY
        if not key:
            return {}

        genai.configure(api_key=key)
        model_id = model_name or settings.SOCRATES_STANDARD_MODEL
        model = genai.GenerativeModel(model_id)

        prompt = f"""
        Extract the following metadata from the text of a document's first page:
        - Author (The organization or person who wrote the report)
        - Publication Date (In YYYY-MM-DD format)

        Text:
        {text[:3000]}

        Return ONLY a valid JSON object with keys "author" and "date". If you cannot find a value, use null.
        Example: {{"author": "UNICEF", "date": "2023-05-15"}}
        """

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=100,
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        import json

        return json.loads(response.text)
    except Exception as e:
        logger.warning(f"LLM metadata extraction failed: {e}")
        return {}


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
    if not parsed_pdf:
        logger.error(f"Tika failed to parse PDF: {filename}")
        raise RuntimeError(f"Tika failed to parse PDF: {filename}")

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

    return {
        "metadata": metadata,
        "document_language": langcode_to_name.get_lang_name(metadata.get("language", "en")),
        "document_title": doc_title,
        "document_summary": doc_summary_text,
        "content": content_as_pages[:4] if len(content_as_pages) >= 4 else content_as_pages,
        "report_type": detect_report_type(content_as_pages[0]),
        "locations": detected_potential_countries(cleaned_content),
        "full_content": cleaned_content,
        "markdown_text": None,
        "document_theme": theme_detection.detect_theme(
            cleaned_content,
            str(BASE_DIR / settings.THEME_MODEL_PATH),
            str(BASE_DIR / settings.THEME_VECTORIZER_PATH),
            theme_detection.themes_list(),
        ),
        "new_detected_disasters": get_disasters(cleaned_content),
        "keywords": generate_keywords(doc_summary_text or "", kw_num),
    }


# Base directory for the project
BASE_DIR = Path(__file__).parent.parent.parent


def detect_v2(
    file_content: bytes, kw_num: int, api_key: str | None, instruct_dict: dict[str, Any], model_name: str | None = None
) -> dict[str, Any]:
    import fitz

    # Ensure all instruction flags exist (all lowercase for robustness)
    data_to_extract = [
        "return_all",
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
    ]
    # Default to True if missing (for frontend standard mode)
    for key in data_to_extract:
        if key not in instruct_dict:
            instruct_dict[key] = True

    if instruct_dict.get("return_all") or instruct_dict.get("Return_ALL"):
        for key in data_to_extract:
            instruct_dict[key] = True

    try:
        pdf = fitz.open(stream=file_content, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF with fitz: {e}")
        raise RuntimeError(f"Cannot open PDF: {e}")

    # Metadata extraction
    chars_per_page = []
    metadata = pdf.metadata
    try:
        for page in pdf:
            chars_per_page.append(len(page.get_text()))
        metadata["charsPerPage"] = chars_per_page
        metadata["No.of Pages"] = pdf.page_count

        # Initial extraction from PDF metadata (handle various casings)
        author = metadata.get("author") or metadata.get("Author") or metadata.get("creator")
        creation_date_raw = metadata.get("creationDate") or metadata.get("CreationDate") or ""
        mod_date_raw = metadata.get("modDate") or metadata.get("ModDate") or ""

        creation_date = convert_date(creation_date_raw)
        mod_date = convert_date(mod_date_raw)

        # LLM Fallback for missing critical metadata
        if not author or not creation_date:
            first_page_text = pdf[0].get_text() if pdf.page_count > 0 else ""
            if first_page_text:
                llm_meta = extract_metadata_with_llm(first_page_text, api_key, model_name)
                author = author or str(llm_meta.get("author") or "")
                creation_date = creation_date or str(llm_meta.get("date") or "")

        metadata["Author"] = author or "Item could not be extracted. Please submit a bug report if concerned."
        metadata["doc_created_date"] = creation_date
        metadata["doc_modified_date"] = mod_date

    except Exception as e:
        logger.warning(f"Metadata extraction partially failed: {e}")
        if "Author" not in metadata:
            metadata["Author"] = "Item could not be extracted. Please submit a bug report if concerned."

    # Title extraction
    try:
        if pdf.page_count > 0:
            titles_list, page1_text = title_detection.print_titles(pdf[0])
        else:
            titles_list, page1_text = [], ""
    except Exception as e:
        logger.error(f"Title extraction failed: {e}")
        titles_list, page1_text = [], ""
    doc_title = titles_list if instruct_dict["document_title"] else None

    content_as_pages = [page.get_text("text") for page in pdf]
    # Heuristic summary fallback
    doc_summary_heuristic = get_doc_summary(content_as_pages[:6] if len(content_as_pages) >= 6 else content_as_pages)
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

    final_summary = doc_summary_heuristic
    if instruct_dict["document_summary"]:
        from src.shared import clean_text as clean_text_mod

        cleaned_for_summary = clean_text_mod.clean_text(cleaned_content)
        generated_summary = summary_generation.make_summary_with_API(cleaned_for_summary, api_key, model_name)
        # Use generated summary if it worked (doesn't start with warning emoji)
        if generated_summary and not generated_summary.startswith("⚠️"):
            final_summary = generated_summary

    pdf.close()
    gc.collect()

    return {
        "metadata": metadata,
        "document_language": doc_language,
        "document_title": doc_title,
        "document_summary": final_summary,
        "content": display_content,
        "report_type": doc_report_type,
        "locations": locations,
        "full_content": cleaned_content if instruct_dict["full_content"] else None,
        "markdown_text": markdown_text,
        "document_theme": themes_detected,
        "new_detected_disasters": new_disasters,
        "disasters": new_disasters,  # Compatibility key
        "keywords": generate_keywords(final_summary or "", kw_num),
    }
