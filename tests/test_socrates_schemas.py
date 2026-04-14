from src.socrates.schemas import SocratesRequest, SocratesResponse, SocratesState


def test_socrates_request():
    req = SocratesRequest(input="What is life?", session_id="test_session")
    assert req.input == "What is life?"
    assert req.session_id == "test_session"
    assert req.channel == "chat"


def test_socrates_state():
    state = SocratesState(raw_input="What is life?", session_id="test_session", run_id="test_run")
    assert state.raw_input == "What is life?"
    assert state.risk_level == "medium"
    assert state.selected_model == "gemini-2.0-flash"
    assert state.assumptions == []


def test_socrates_response():
    resp = SocratesResponse(run_id="test_run", output="Life is a journey.")
    assert resp.run_id == "test_run"
    assert resp.output == "Life is a journey."
    assert resp.artifact_id is None
