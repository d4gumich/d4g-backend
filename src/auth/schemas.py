from pydantic import BaseModel


class SessionCreate(BaseModel):
    provider: str
    model: str
    api_key: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    status: str
