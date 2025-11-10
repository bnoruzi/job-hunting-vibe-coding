"""SerpAPI-powered LinkedIn job search provider."""

from __future__ import annotations

import requests

from .. import config
from ..utils.logging import get_logger, log_latency

logger = get_logger(__name__)

_SERP_API_ENDPOINT = "https://serpapi.com/search.json"


def _get_settings() -> dict[str, object]:
    return config.PROVIDER_SETTINGS.get("serpapi_linkedin", {})


_DATE_POSTED_TBS = {
    "past_24_hours": "qdr:d",
    "past_week": "qdr:w",
    "past_month": "qdr:m",
}


def _build_query(role: str, location: str, filters: dict[str, object]) -> tuple[str, dict[str, str]]:
    query_parts = [f"{role} in {location}", "site:linkedin.com/jobs"]
    params: dict[str, str] = {}

    job_type = filters.get("job_type")
    if isinstance(job_type, str) and job_type:
        query_parts.append(job_type)

    keywords = filters.get("keywords")
    if isinstance(keywords, str) and keywords:
        query_parts.append(keywords)

    date_key = filters.get("date_posted")
    if isinstance(date_key, str):
        tbs_value = _DATE_POSTED_TBS.get(date_key)
        if tbs_value:
            params["tbs"] = tbs_value

    return " ".join(query_parts), params


def search(role: str, location: str, limit: int, filters: dict[str, object] | None = None):
    """Search LinkedIn job listings using SerpAPI."""
    settings = _get_settings()
    api_key = settings.get("api_key") or config.SERPAPI_KEY
    if not api_key:
        raise ValueError("SERPAPI key is not configured for the LinkedIn provider")

    active_filters: dict[str, object] = filters or {}
    query, extra_params = _build_query(role, location, active_filters)

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
    }
    params.update(extra_params)
    if limit:
        params["num"] = limit

    timeout = settings.get("timeout", config.PROVIDER_REQUEST_TIMEOUT)
    with log_latency(
        logger,
        "serpapi.request",
        provider="serpapi_linkedin",
        role=role,
        location=location,
    ):
        response = requests.get(_SERP_API_ENDPOINT, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()

    results = []
    for item in payload.get("organic_results", []):
        link = item.get("link")
        if not link:
            continue
        metadata = {}
        if item.get("date"):
            metadata["posted_at"] = item.get("date")
        if item.get("snippet"):
            metadata["snippet"] = item.get("snippet")
        if item.get("displayed_link"):
            metadata["displayed_link"] = item.get("displayed_link")
        if item.get("position") is not None:
            metadata["position"] = str(item.get("position"))

        results.append(
            {
                "title": item.get("title"),
                "link": link,
                "source": settings.get("label", "LinkedIn (SerpAPI)"),
                "metadata": metadata,
            }
        )

    return results[:limit] if limit else results
