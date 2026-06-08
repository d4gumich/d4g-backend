from pydantic import BaseModel


class ChetahQuery(BaseModel):
    query: str


class ChetahResult(BaseModel):
    title: str | None = None
    date: str | None = None
    link: str | None = None
    cluster: str | None = None
    summary_short: str | None = None
    summary_full: str | None = None

    # V2 fields
    report_title: list[str] | str | None = None
    report_author: str | None = None
    organization_name: str | None = None
    doc_creation_date: str | None = None
    doc_modified_date: str | None = None
    year_of_report: str | int | None = None
    report_type: str | None = None
    pages_in_report: str | int | None = None
    language_of_doc: str | None = None
    locations_report: list[str] | str | None = None
    themes: list[str] | str | None = None
    summary: str | None = None
    file_name: str | None = None
    error: str | None = None


class ChetahResponse(BaseModel):
    results: list[ChetahResult]
