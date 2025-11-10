"""Collection of pluggable job search providers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_CACHE: dict[tuple[str, str | None], Any] = {}
_PACKAGE_ROOT = __name__.rsplit(".", 1)[0]


def _resolve_import_path(module_path: str) -> tuple[str, str | None]:
    if module_path.startswith("."):
        return module_path, _PACKAGE_ROOT
    if module_path.startswith(_PACKAGE_ROOT):
        return module_path, None
    if "." not in module_path:
        module_path = f"providers.{module_path}"
    if module_path.startswith("providers."):
        return f".{module_path}", _PACKAGE_ROOT
    return f".{module_path}", _PACKAGE_ROOT


def load(module_path: str) -> Any:
    """Import and cache a provider module by its dotted path."""
    resolved_path, package = _resolve_import_path(module_path)
    cache_key = (resolved_path, package)
    if cache_key not in _CACHE:
        _CACHE[cache_key] = import_module(resolved_path, package=package)
    return _CACHE[cache_key]
