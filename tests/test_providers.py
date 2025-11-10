import pytest

from src import config
from src.providers import serpapi_indeed, serpapi_linkedin


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):  # pragma: no cover - nothing to do
        return None

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_provider_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "PROVIDER_SETTINGS",
        {
            "serpapi_indeed": {
                "enabled": True,
                "api_key": "indeed-key",
                "result_limit": 5,
                "module": "providers.serpapi_indeed",
                "label": "Indeed (SerpAPI)",
            },
            "serpapi_linkedin": {
                "enabled": True,
                "api_key": "linkedin-key",
                "result_limit": 5,
                "module": "providers.serpapi_linkedin",
                "label": "LinkedIn (SerpAPI)",
            },
        },
    )
    monkeypatch.setattr(config, "SERPAPI_KEY", "fallback-key")
    monkeypatch.setattr(config, "PROVIDER_REQUEST_TIMEOUT", 5.0)


def test_serpapi_indeed_search_builds_results(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_params = {}

    def fake_get(url, params, timeout):
        captured_params.update(params)
        payload = {
            "organic_results": [
                {
                    "title": "Senior Engineer",
                    "link": "https://indeed.example/job/123",
                    "snippet": "Great role",
                    "date": "2024-01-01",
                    "displayed_link": "indeed.com",
                    "position": 1,
                }
            ]
        }
        return DummyResponse(payload)

    monkeypatch.setattr(serpapi_indeed.requests, "get", fake_get)

    results = serpapi_indeed.search(
        "Software Engineer", "Toronto", limit=3, filters={"keywords": "python"}
    )

    assert len(results) == 1
    assert results[0]["link"] == "https://indeed.example/job/123"
    assert results[0]["metadata"]["posted_at"] == "2024-01-01"
    assert captured_params["q"].startswith("Software Engineer in Toronto")
    assert captured_params["num"] == 3


def test_serpapi_linkedin_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = config.PROVIDER_SETTINGS["serpapi_linkedin"].copy()
    settings["api_key"] = ""
    monkeypatch.setitem(config.PROVIDER_SETTINGS, "serpapi_linkedin", settings)
    monkeypatch.setattr(config, "SERPAPI_KEY", "")

    with pytest.raises(ValueError):
        serpapi_linkedin.search("Data Scientist", "Remote", limit=2, filters=None)


def test_serpapi_linkedin_search(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_params = {}

    def fake_get(url, params, timeout):
        captured_params.update(params)
        payload = {
            "organic_results": [
                {
                    "title": "ML Engineer",
                    "link": "https://linkedin.example/job/456",
                    "snippet": "Exciting opportunity",
                    "date": "2024-02-02",
                    "displayed_link": "linkedin.com",
                    "position": 2,
                }
            ]
        }
        return DummyResponse(payload)

    monkeypatch.setattr(serpapi_linkedin.requests, "get", fake_get)

    results = serpapi_linkedin.search(
        "Machine Learning Engineer", "Vancouver", limit=2, filters={}
    )

    assert len(results) == 1
    assert results[0]["source"] == "LinkedIn (SerpAPI)"
    assert captured_params["num"] == 2
    assert "linkedin.com/jobs" in captured_params["q"]
