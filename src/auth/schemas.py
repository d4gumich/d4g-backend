from pydantic import BaseModel


class SessionCreate(BaseModel):
    provider: str
    model: str
    api_key: str | None = None


class SessionResponse(BaseModel):
    status: str
    csrf_token: str


class ModelsRequest(BaseModel):
    provider: str
    api_key: str | None = None


class ModelInfo(BaseModel):
    id: str
    name: str
    tier: str | None = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]
    status: str
