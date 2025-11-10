"""Notification helpers for high-value enrichment results."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from .logging import get_logger

logger = get_logger(__name__)


def send_high_score_alert(
    *,
    score: float,
    posting: Mapping[str, Any] | None = None,
    enrichment: Mapping[str, Any] | None = None,
) -> None:
    """Emit a structured log representing an alert for a high scoring job."""

    context: MutableMapping[str, Any] = {
        "event": "notification.high_score",
        "score": score,
    }
    if posting:
        context["job_title"] = posting.get("title")
        context["job_link"] = posting.get("link")
        context["job_source"] = posting.get("source") or posting.get("provider")
    if enrichment:
        context["ai_summary"] = enrichment.get("ai_summary")

    logger.info("notification.high_score", extra=context)
