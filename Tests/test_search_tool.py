from agent_service.tools import search


class _FakeDDGS:
    def __init__(self, results):
        self._results = results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def text(self, query, max_results=3):
        assert query == "OpenAI latest models"
        assert max_results == 3
        return self._results


def test_web_search_returns_formatted_results(monkeypatch):
    fake_results = [
        {
            "title": "Models - OpenAI API",
            "href": "https://developers.openai.com/api/docs/models",
            "body": "Choose the right model for your use case.",
        }
    ]

    monkeypatch.setattr(search, "DDGS", lambda: _FakeDDGS(fake_results))

    result = search.web_search("OpenAI latest models")

    assert result["success"] is True
    assert result["results"] == fake_results
    assert "Models - OpenAI API" in result["message"]


def test_web_search_rejects_empty_query():
    result = search.web_search("   ")

    assert result["success"] is False
    assert result["message"] == "Search query was empty."
