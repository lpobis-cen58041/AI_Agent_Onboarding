"""Offline checks for the Confluence workflow retained after cleanup."""
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def wiki(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / ".github/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("wiki")
    monkeypatch.setattr(module.sw, "_load_secrets_file", lambda: None)
    return module


def test_configured_cookie_does_not_require_browser(wiki, monkeypatch):
    monkeypatch.delenv("CONFLUENCE_TOKEN", raising=False)
    monkeypatch.setenv("CONFLUENCE_COOKIE", "synthetic-session")
    monkeypatch.setattr(wiki.sw, "_NO_BROWSER", True)
    assert wiki.sw._auth_headers() == {"Cookie": "synthetic-session"}


def test_no_browser_without_credentials_reports_auth_failure(wiki, monkeypatch, capsys):
    monkeypatch.delenv("CONFLUENCE_TOKEN", raising=False)
    monkeypatch.delenv("CONFLUENCE_COOKIE", raising=False)
    monkeypatch.setattr(wiki.sw, "_NO_BROWSER", True)
    with pytest.raises(SystemExit) as error:
        wiki.sw._auth_headers()
    assert error.value.code == 1
    assert "disabled via --no-browser" in capsys.readouterr().err


def test_write_and_compare_snapshots(wiki, monkeypatch, tmp_path):
    snapshots = tmp_path / "wiki"
    snapshots.mkdir()
    (snapshots / "obsolete.md").write_text("obsolete", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(wiki, "WIKI", snapshots)
    monkeypatch.setattr(wiki, "MANIFEST", manifest)
    pages = {"guide.md": {"id": 123, "title": "Guide", "depth": 0,
                          "md": "# Guide\n", "ver": 2}}
    wiki.write_all(pages)
    assert not (snapshots / "obsolete.md").exists()
    assert (snapshots / "guide.md").read_text(encoding="utf-8") == "# Guide\n"
    assert "Pages: 1" in (snapshots / "_INDEX.md").read_text(encoding="utf-8")
    assert json.loads(manifest.read_text())["wiki_pages"][0]["confluence_version"] == 2
    assert wiki.compare(pages) == 0
    pages["guide.md"]["md"] = "# Updated\n"
    assert wiki.compare(pages) == 1


def test_fetch_tree_and_extra_page(wiki, monkeypatch):
    def get(path):
        if path == "/rest/api/content/100":
            return {"title": "Root"}
        assert path == "/rest/api/content/300?expand=body.export_view,version"
        return {"title": "Extra", "status": "current", "version": {"number": 4},
                "body": {"export_view": {"value": "<p>Extra content</p>"}}}

    monkeypatch.setattr(wiki.sw, "_confluence_get", get)
    monkeypatch.setattr(wiki.sw, "_fetch_page_markdown",
                        lambda pid, title: (f"# {title}\n", 1))
    monkeypatch.setattr(wiki, "children",
                        lambda pid: [{"id": 200, "title": "Child"}] if pid == 100 else [])
    pages = wiki.fetch_all({"trees": [{"root_id": 100}],
                            "extra_pages": [{"id": 300, "file": "extra.md"}]})
    assert {page["id"] for page in pages.values()} == {100, 200, 300}
    assert pages["root-100.md"]["depth"] == 0
    assert pages["child-200.md"]["depth"] == 1
    assert "Extra content" in pages["extra.md"]["md"]
