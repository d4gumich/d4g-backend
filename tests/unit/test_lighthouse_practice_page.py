from src.core.settings import settings
from src.lighthouse.practice_page import practice_code_ok, practice_file


def test_a_short_or_empty_code_never_matches(monkeypatch):
    monkeypatch.setattr(settings, "LIGHTHOUSE_DEV_PAGE_CODE", "")
    assert practice_code_ok("a" * 32) is False
    monkeypatch.setattr(settings, "LIGHTHOUSE_DEV_PAGE_CODE", "too-short")
    assert practice_code_ok("too-short") is False


def test_only_the_configured_code_matches(monkeypatch):
    code = "a" * 32
    monkeypatch.setattr(settings, "LIGHTHOUSE_DEV_PAGE_CODE", code)
    assert practice_code_ok(code) is True
    assert practice_code_ok("b" * 32) is False
    assert practice_code_ok(code + "x") is False


def test_practice_files_stay_inside_the_page_directory(tmp_path, monkeypatch):
    page = tmp_path / "index.html"
    page.write_text("ok")
    nested = tmp_path / "assets"
    nested.mkdir()
    script = nested / "app.js"
    script.write_text("console.log(1)")
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret")
    monkeypatch.setattr("src.lighthouse.practice_page.PAGE_ROOT", tmp_path)
    assert practice_file("") == page
    assert practice_file("assets/app.js") == script
    assert practice_file("assets/../../../outside.txt") is None
    assert practice_file("../outside.txt") is None
    assert practice_file("missing.js") is None
    outside.unlink()
