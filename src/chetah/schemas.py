from pydantic import BaseModel
from typing import List, Optional

class ChetahQuery(BaseModel):
    query: str

class ChetahResult(BaseModel):
    title: str
    date: Optional[str] = None
    link: str
    cluster: Optional[str] = None
    summary_short: str
    summary_full: str

class ChetahResponse(BaseModel):
    results: List[ChetahResult]
