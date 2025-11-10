import json

import pytest
import requests

from src import config
from src.ai import enrichment


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):  # pragma: no cover - nothing to do
        return None

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def configure_ai_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "AI_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr(config, "AI_PROVIDER", "openai")
    monkeypatch.setattr(config, "AI_MODEL", "gpt-test")
    monkeypatch.setattr(config, "AI_API_KEY", "api-key")
    monkeypatch.setattr(config, "AI_ORG", None)
    monkeypatch.setattr(config, "AI_BASE_URL", "https://api.example")
    monkeypatch.setattr(config, "AI_COMPLETIONS_URL", "https://api.example/v1/chat/completions")
    monkeypatch.setattr(config, "AI_TEMPERATURE", 0.0)
    monkeypatch.setattr(config, "AI_TIMEOUT", 5.0)
    monkeypatch.setattr(config, "AI_MAX_RETRIES", 2)
    monkeypatch.setattr(config, "AI_RETRY_BACKOFF_SECONDS", 0)
    monkeypatch.setattr(config, "AI_RESPONSE_FORMAT_JSON", True)
    monkeypatch.setattr(
        config,
        "AI_PROMPT_TEMPLATES",
        {
            "system": "system",
            "user": "Job Title: {job_title}\nDescription: {description}",
            "candidate_profile": "Candidate",
        },
    )
    monkeypatch.setattr(config, "AI_ENRICHMENT_ALERTS_ENABLED", False)
    monkeypatch.setattr(config, "AI_ENRICHMENT_ALERT_THRESHOLD", 0.0)


def test_enrich_job_success_sends_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "AI_ENRICHMENT_ALERTS_ENABLED", True)
    monkeypatch.setattr(config, "AI_ENRICHMENT_ALERT_THRESHOLD", 70.0)

    alerts = []

    def fake_alert(**kwargs):
        alerts.append(kwargs)

    monkeypatch.setattr(enrichment.notifications, "send_high_score_alert", fake_alert)

    def fake_post(url, headers=None, **kwargs):
        assert url == config.AI_COMPLETIONS_URL
        json_payload = kwargs.get("json")
        assert json_payload["model"] == config.AI_MODEL
        assert any(
            message["role"] == "user" and message["content"].startswith("Job Title:")
            for message in json_payload["messages"]
        )
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "fit_score": 82,
                                "summary": "Strong match",
                                "outreach_angle": "Reach out via LinkedIn",
                            }
                        )
                    }
                }
            ]
        }
        return DummyResponse(payload)

    monkeypatch.setattr(enrichment.requests, "post", fake_post)

    posting = {"title": "Engineer", "link": "https://jobs/1"}
    result = enrichment.enrich_job(posting)

    assert result["ai_fit_score"] == 82
    assert result["ai_summary"] == "Strong match"
    assert len(alerts) == 1
    assert alerts[0]["score"] == 82
    assert alerts[0]["posting"] == posting


def test_enrich_job_retries_and_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = []

    def fake_post(*args, **kwargs):
        attempts.append(1)
        raise requests.RequestException("boom")

    monkeypatch.setattr(enrichment.requests, "post", fake_post)
    monkeypatch.setattr(enrichment.time, "sleep", lambda _: None)

    with pytest.raises(enrichment.EnrichmentError) as exc:
        enrichment.enrich_job({"title": "Engineer"})

    assert "boom" in str(exc.value)
    assert len(attempts) == config.AI_MAX_RETRIES
