from pydantic import BaseModel


class ChetahQuery(BaseModel):
    query: str


class ChetahResult(BaseModel):
    title: str
    date: str | None = None
    link: str
    cluster: str | None = None
    summary_short: str
    summary_full: str


class ChetahResponse(BaseModel):
    results: list[ChetahResult]
