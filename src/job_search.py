"""Job search dispatcher that aggregates results from configured providers."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from . import config
from .providers import load as load_provider

_REQUIRED_PROVIDER_KEYS = ("module", "result_limit")


def _iter_enabled_providers() -> Iterable[tuple[str, Dict[str, object]]]:
    for name, settings in config.PROVIDER_SETTINGS.items():
        if settings.get("enabled", True):
            yield name, settings


def search_jobs_for_role(
    role: str,
    locations: Iterable[str],
    filters: Optional[Dict[str, object]] = None,
) -> List[Dict[str, object]]:
    """Query all enabled providers for the given role and merge the results.

    Args:
        role: The job title or keyword to search for.
        locations: Locations to search against.
        filters: Optional filters to forward to each provider.

    Returns:
        A list of provider results with duplicates removed by URL.
    """

    aggregated: List[Dict[str, object]] = []
    seen_links = set()
    active_filters = filters or {}

    for location in locations:
        for provider_name, settings in _iter_enabled_providers():
            for key in _REQUIRED_PROVIDER_KEYS:
                if key not in settings:
                    raise ValueError(
                        f"Provider '{provider_name}' missing required setting '{key}'"
                    )

            provider_module = load_provider(settings["module"])
            limit = int(settings.get("result_limit", config.DEFAULT_PROVIDER_LIMIT))

            try:
                provider_results = provider_module.search(role, location, limit, active_filters)
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"[WARN] Provider {provider_name} failed: {exc}")
                continue

            for item in provider_results:
                link = item.get("link")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                item.setdefault("source", settings.get("label", provider_name))
                item.setdefault("provider", provider_name)
                metadata = item.setdefault("metadata", {})
                metadata.setdefault("location", location)
                aggregated.append(item)

    return aggregated
