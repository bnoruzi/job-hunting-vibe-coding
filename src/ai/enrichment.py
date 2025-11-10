"""Job posting enrichment powered by large language models."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import requests

from .. import config

logger = logging.getLogger(__name__)


class EnrichmentError(RuntimeError):
    """Raised when enrichment cannot be completed."""


@dataclass
class _PromptPayload:
    system_prompt: str
    user_prompt: str


def _build_prompt(posting: Mapping[str, Any]) -> _PromptPayload:
    metadata = posting.get("metadata") if isinstance(posting, Mapping) else None
    metadata = metadata if isinstance(metadata, Mapping) else {}

    title = str(posting.get("title") or metadata.get("title") or "").strip()
    company = str(posting.get("company") or metadata.get("company") or "").strip()
    location = str(posting.get("location") or metadata.get("location") or "").strip()
    description = str(
        posting.get("description")
        or metadata.get("description")
        or metadata.get("snippet")
        or ""
    ).strip()

    link = str(posting.get("link") or metadata.get("link") or "").strip()

    system_prompt = config.AI_PROMPT_TEMPLATES.get("system", "").strip()
    user_template = config.AI_PROMPT_TEMPLATES.get("user", "").strip()
    candidate_profile = config.AI_PROMPT_TEMPLATES.get("candidate_profile", "").strip()

    if not user_template:
        raise EnrichmentError("AI user prompt template is not configured.")

    user_prompt = user_template.format(
        candidate_profile=candidate_profile,
        job_title=title,
        company=company,
        location=location,
        description=description,
        link=link,
    )

    return _PromptPayload(system_prompt=system_prompt, user_prompt=user_prompt)


def _request_headers() -> Dict[str, str]:
    if not config.AI_API_KEY:
        raise EnrichmentError("AI_API_KEY is required for enrichment.")

    provider = (config.AI_PROVIDER or "openai").lower()
    headers = {"Content-Type": "application/json"}
    if provider == "azure":
        headers["api-key"] = config.AI_API_KEY
    else:
        headers["Authorization"] = f"Bearer {config.AI_API_KEY}"
    if config.AI_ORG:
        headers["OpenAI-Organization"] = config.AI_ORG
    return headers


def _completions_url() -> str:
    if config.AI_COMPLETIONS_URL:
        return config.AI_COMPLETIONS_URL
    base = config.AI_BASE_URL.rstrip("/") if config.AI_BASE_URL else "https://api.openai.com/v1"
    return f"{base}/chat/completions"


def _compose_payload(prompt: _PromptPayload) -> Dict[str, Any]:
    messages = []
    if prompt.system_prompt:
        messages.append({"role": "system", "content": prompt.system_prompt})
    messages.append({"role": "user", "content": prompt.user_prompt})

    payload: Dict[str, Any] = {
        "model": config.AI_MODEL,
        "messages": messages,
        "temperature": config.AI_TEMPERATURE,
    }
    if config.AI_RESPONSE_FORMAT_JSON:
        payload["response_format"] = {"type": "json_object"}
    return payload


def _parse_response_content(content: str) -> Dict[str, Any]:
    text = content.strip()
    if not text:
        raise ValueError("Empty response from AI provider")
    if "```" in text:
        segments = text.split("```")
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            if segment.startswith("json"):
                segment = segment[4:].strip()
            if segment.startswith("{") and segment.endswith("}"):
                text = segment
                break
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response is not valid JSON: {exc}") from exc
    return payload


def _normalize_result(data: Mapping[str, Any]) -> Dict[str, Any]:
    fit_score = data.get("fit_score") or data.get("score") or data.get("fitScore")
    summary = data.get("summary") or data.get("highlights")
    outreach = data.get("outreach_angle") or data.get("outreach")

    result = {
        "ai_fit_score": fit_score or "",
        "ai_summary": summary or "",
        "ai_outreach_angle": outreach or "",
    }
    additional = data.get("additional_context")
    if isinstance(additional, Mapping):
        for key, value in additional.items():
            normalized_key = str(key).strip().lower().replace(" ", "_")
            if not normalized_key:
                continue
            result[f"ai_extra_{normalized_key}"] = value
    return result


def enrich_job(posting: Mapping[str, Any]) -> Dict[str, Any]:
    """Return AI enrichment for a job posting.

    Args:
        posting: Raw job posting payload.

    Returns:
        A dictionary with normalized enrichment columns.

    Raises:
        EnrichmentError: If the enrichment fails after exhausting retries.
    """

    if not config.AI_ENRICHMENT_ENABLED:
        return {}

    prompt = _build_prompt(posting)
    url = _completions_url()
    payload = _compose_payload(prompt)
    headers = _request_headers()
    timeout = config.AI_TIMEOUT
    max_attempts = max(1, config.AI_MAX_RETRIES)

    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices")
            if not choices:
                raise ValueError("AI response missing choices array")
            message = choices[0].get("message", {})
            content = message.get("content")
            if not isinstance(content, str):
                raise ValueError("AI response content is not text")
            parsed = _parse_response_content(content)
            normalized = _normalize_result(parsed)
            return normalized
        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning(
                "AI enrichment attempt %s/%s failed: %s", attempt, max_attempts, exc
            )
            if attempt < max_attempts:
                time.sleep(config.AI_RETRY_BACKOFF_SECONDS)
                continue
            break

    error_message = (
        str(last_error) if last_error else "Unknown AI enrichment failure"
    )
    raise EnrichmentError(error_message)
