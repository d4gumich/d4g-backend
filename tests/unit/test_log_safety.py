import logging
import re

import pytest

from src.core.settings import settings
from src.shared.log_safety import (
    accept_request_id,
    begin_request_log,
    finish_request_log,
    install_log_redaction,
    redact_text,
    remember_log_secret,
)


def test_request_ids_keep_a_safe_header_and_replace_anything_else():
    assert accept_request_id("abc_DEF-1234") == "abc_DEF-1234"
    assert re.fullmatch(r"[a-f0-9]{12}", accept_request_id("bad id"))
    assert re.fullmatch(r"[a-f0-9]{12}", accept_request_id(None))
    assert accept_request_id("short") != "short"


def test_redaction_removes_provider_shapes_and_keeps_ordinary_words():
    text = redact_text(
        "lookup failed for AIzaSyA1234567890123456789012 "
        "sk-ant-abcdefghij123456 sk-abcdefghijklmnopqrstuvwxyz "
        "hf_abcdefghijklmnopqrstuvwxyz Bearer super-secret-token "
        'api_key="visitor-key-value"'
    )
    assert "AIzaSyA" not in text
    assert "sk-ant-" not in text
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in text
    assert "hf_abcdefghijklmnopqrstuvwxyz" not in text
    assert "super-secret-token" not in text
    assert "visitor-key-value" not in text
    assert "lookup failed" in text
    assert "[redacted]" in text


def test_a_short_remembered_secret_is_removed_from_the_log(caplog):
    install_log_redaction()
    request_id, id_token, secret_token = begin_request_log(None)
    remember_log_secret("test-key")
    remember_log_secret("tiny")
    try:
        with caplog.at_level(logging.ERROR):
            try:
                raise RuntimeError("rejected test-key and tiny")
            except RuntimeError:
                logging.getLogger("test.log_safety").exception("sign-in failed")
        assert "test-key" not in caplog.text
        assert "tiny" in caplog.text
        assert "[redacted]" in caplog.text
        assert request_id
    finally:
        finish_request_log(id_token, secret_token)


def test_configured_server_secrets_are_removed(caplog, monkeypatch):
    monkeypatch.setattr(settings, "HF_TOKEN", "hf-server-secret-value")
    monkeypatch.setattr(settings, "SOCRATES_DB_URL", "postgresql://socrates:db-password-value@localhost/socrates")
    install_log_redaction()
    with caplog.at_level(logging.ERROR):
        logging.getLogger("test.log_safety.config").error(
            "token hf-server-secret-value url postgresql://socrates:db-password-value@localhost/socrates"
        )
    assert "hf-server-secret-value" not in caplog.text
    assert "db-password-value" not in caplog.text
    assert "token [redacted]" in caplog.text


def test_ordinary_messages_are_not_rewritten(caplog):
    install_log_redaction()
    with caplog.at_level(logging.INFO):
        logging.getLogger("test.log_safety.plain").info("Model lookup failed")
    assert "Model lookup failed" in caplog.text


@pytest.fixture(autouse=True)
def _isolate_request_secrets():
    _request_id, id_token, secret_token = begin_request_log(None)
    yield
    finish_request_log(id_token, secret_token)
