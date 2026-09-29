import pytest
from cryptography.fernet import Fernet, InvalidToken

from src.shared.session import SessionStore, master_fernet


def test_master_key_is_stable_for_a_dedicated_secret_and_ignores_other_secrets():
    primary = master_fernet("dedicated-session-secret")
    again = master_fernet("dedicated-session-secret")
    token = primary.encrypt(b"visitor-key")
    assert again.decrypt(token) == b"visitor-key"
    with pytest.raises(InvalidToken):
        master_fernet("google-api-key-value").decrypt(token)


def test_api_key_is_encrypted_at_rest_and_a_tampered_value_fails_closed():
    store = SessionStore(cipher=Fernet(Fernet.generate_key()))
    session_id = store.create_session({"api_key": "super-secret-value", "provider": "google"})
    stored = store._sessions[session_id]["data"]["api_key"]
    assert "super-secret-value" not in stored
    opened = store.get_session(session_id)
    assert opened is not None
    assert opened["api_key"] == "super-secret-value"

    store._sessions[session_id]["data"]["api_key"] = stored[:-4] + "xxxx"
    assert store.get_session(session_id) is None


def test_session_id_is_unguessable_and_csrf_survives_reads():
    store = SessionStore(cipher=Fernet(Fernet.generate_key()))
    session_id = store.create_session({"api_key": "k"})
    assert len(session_id) >= 43
    assert session_id.count("-") != 4
    first = store.peek_csrf(session_id)
    assert first and len(first) >= 43
    assert store.peek_csrf(session_id) == first
    assert store.peek_csrf("missing") is None


def test_sliding_access_cannot_extend_past_the_absolute_lifetime():
    now = [1_000.0]
    store = SessionStore(ttl=30, absolute_ttl=100, clock=lambda: now[0], cipher=Fernet(Fernet.generate_key()))
    session_id = store.create_session({"api_key": "k"})
    for stamp in (1_020, 1_045, 1_070, 1_095):
        now[0] = stamp
        refreshed = store.get_session(session_id)
        assert refreshed is not None
        assert refreshed["api_key"] == "k"
    now[0] = 1_101
    assert store.get_session(session_id) is None


def test_explicit_ttl_is_a_hard_stop():
    now = [1_000.0]
    store = SessionStore(ttl=30, absolute_ttl=10_000, clock=lambda: now[0], cipher=Fernet(Fernet.generate_key()))
    session_id = store.create_session({"note": "lighthouse"}, ttl=50)
    now[0] = 1_040
    still_open = store.get_session(session_id)
    assert still_open is not None
    assert still_open["note"] == "lighthouse"
    now[0] = 1_051
    assert store.get_session(session_id) is None


def test_logout_removes_the_server_session():
    store = SessionStore(cipher=Fernet(Fernet.generate_key()))
    session_id = store.create_session({"api_key": "k"})
    store.delete_session(session_id)
    assert store.get_session(session_id) is None
    assert store.peek_csrf(session_id) is None


def test_store_refuses_new_sessions_when_full():
    from src.shared.session import SessionCapacityError

    store = SessionStore(max_sessions=1, cipher=Fernet(Fernet.generate_key()))
    store.create_session({"api_key": "a"})
    with pytest.raises(SessionCapacityError):
        store.create_session({"api_key": "b"})


def test_session_module_does_not_derive_from_the_owl_api_key():
    from pathlib import Path

    source = Path("src/shared/session.py").read_text()
    assert "OWL_GOOGLE_API_KEY" not in source


def test_resolve_never_treats_experimental_or_team_sessions_as_personal_keys():
    from src.shared.byok import resolve_byok
    from src.shared.session import session_store

    personal = session_store.create_session(
        {"api_key": "visitor-key", "provider": "google", "selected_model": "gemini-2.5-flash-lite"}
    )
    experimental = session_store.create_session({"is_lighthouse": True, "api_key": "experimental-secret"})
    try:
        creds = resolve_byok(personal)
        assert creds.personal is True
        assert creds.api_key == "visitor-key"
        assert creds.key_source == "personal"
        forced = resolve_byok(personal, force_team=True)
        assert forced.api_key is None
        assert forced.key_source == "team"
        blocked = resolve_byok(experimental)
        assert blocked.api_key is None
        assert blocked.key_source == "none"
    finally:
        session_store.delete_session(personal)
        session_store.delete_session(experimental)


def test_csrf_gates_live_sessions_and_logout_stays_reachable():
    from src.shared.byok import csrf_rejected
    from src.shared.session import session_store

    session_id = session_store.create_session({"api_key": "visitor-key"})
    token = session_store.peek_csrf(session_id)
    try:
        assert csrf_rejected("POST", "/api/v1/products/owl", session_id, None, token, None) is False
        assert csrf_rejected("POST", "/api/v1/products/owl", session_id, None, "nope", None) is True
        assert csrf_rejected("POST", "/api/v1/auth/logout", session_id, None, None, None) is False
        assert csrf_rejected("GET", "/api/v1/auth/status", session_id, None, None, None) is False
        assert csrf_rejected("POST", "/api/v1/products/chetah", "missing", None, None, None) is False
    finally:
        session_store.delete_session(session_id)


def test_origin_allowlist_blocks_cross_site_writes():
    from src.shared.byok import origin_rejected

    assert origin_rejected("POST", "https://evil.test", ["https://d4g.test"], "https://api.test") is True
    assert origin_rejected("POST", "https://d4g.test", ["https://d4g.test"], "https://api.test") is False
    assert origin_rejected("POST", "https://api.test", ["https://d4g.test"], "https://api.test") is False
    assert origin_rejected("POST", "https://evil.test", [], "https://api.test") is False
    assert origin_rejected("GET", "https://evil.test", ["https://d4g.test"], "https://api.test") is False


def test_auth_attempt_limiter_resets_after_the_window():
    from src.shared.byok import AttemptLimiter

    now = [0.0]
    limiter = AttemptLimiter(limit=2, window=10, clock=lambda: now[0])
    assert limiter.allow("203.0.113.4") is True
    assert limiter.allow("203.0.113.4") is True
    assert limiter.allow("203.0.113.4") is False
    now[0] = 11
    assert limiter.allow("203.0.113.4") is True


def test_redact_secret_removes_the_visitor_key():
    from src.shared.byok import redact_secret

    assert redact_secret("invalid super-secret-value", "super-secret-value") == "invalid [redacted]"
