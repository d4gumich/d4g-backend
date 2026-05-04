from fastapi import APIRouter, Cookie, HTTPException, Response

from src.auth.schemas import SessionCreate, SessionResponse
from src.shared.llm_factory import validate_key
from src.shared.session import session_store

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/session", response_model=SessionResponse)
async def initialize_session(request: SessionCreate, response: Response, session_id: str = Cookie(None)):
    # Case 1: Updating an existing session without a new key
    if not request.api_key:
        if not session_id or not session_store.get_session(session_id):
            raise HTTPException(status_code=401, detail="No active session found. Please provide an API key.")

        # Update only the model/provider metadata
        session_store.update_session(session_id, {"provider": request.provider, "selected_model": request.model})
        return {"session_id": session_id, "status": "success"}

    # Case 2: Creating a new session or updating with a new key
    # Validate the key before creating session
    is_valid, error_detail = await validate_key(request.provider, request.model, request.api_key)
    if not is_valid:
        # Pass through the actual error from the AI provider for better troubleshooting
        raise HTTPException(status_code=401, detail=f"API Key Validation Failed: {error_detail}")

    # Delete old session if it exists to prevent duplicates
    if session_id:
        session_store.delete_session(session_id)

    session_data = {"provider": request.provider, "selected_model": request.model, "api_key": request.api_key}

    new_session_id = session_store.create_session(session_data)

    # Set the HttpOnly cookie
    response.set_cookie(
        key="session_id",
        value=new_session_id,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800,  # 30 minutes
    )

    return {"session_id": new_session_id, "status": "success"}


@router.get("/status")
async def get_session_status(session_id: str = Cookie(None)):
    if session_id:
        session_data = session_store.get_session(session_id)
        if session_data:
            return {
                "status": "active",
                "provider": session_data.get("provider"),
                "model": session_data.get("selected_model"),
            }
    return {"status": "inactive"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_id")
    return {"status": "success"}
