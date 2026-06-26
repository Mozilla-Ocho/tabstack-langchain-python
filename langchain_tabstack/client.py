"""Tabstack client construction.

The API key is read from ``TABSTACK_API_KEY`` by default and can be overridden
explicitly. Every network call in this package goes through this client.
"""

from __future__ import annotations

import os
from typing import Optional

from tabstack import AsyncTabstack, Tabstack

__all__ = [
    "create_tabstack_client",
    "get_default_client",
    "create_async_tabstack_client",
    "get_default_async_client",
]


def _client_kwargs(api_key: Optional[str], base_url: Optional[str]) -> dict:
    resolved_key = api_key if api_key is not None else os.environ.get("TABSTACK_API_KEY")
    kwargs: dict = {"api_key": resolved_key}
    if base_url is not None:
        kwargs["base_url"] = base_url
    return kwargs


def create_tabstack_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Tabstack:
    """Construct a configured synchronous Tabstack client.

    Args:
        api_key: Tabstack API key. Falls back to ``TABSTACK_API_KEY`` when omitted.
        base_url: Override the API base URL. Uses the SDK default when omitted.
    """
    return Tabstack(**_client_kwargs(api_key, base_url))


def create_async_tabstack_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> AsyncTabstack:
    """Construct a configured asynchronous Tabstack client."""
    return AsyncTabstack(**_client_kwargs(api_key, base_url))


_default_client: Optional[Tabstack] = None
_default_async_client: Optional[AsyncTabstack] = None


def get_default_client() -> Tabstack:
    """Lazily construct and reuse a single default sync client.

    The client is only built on first use, so importing this package never
    requires an API key to be set.
    """
    global _default_client
    if _default_client is None:
        _default_client = create_tabstack_client()
    return _default_client


def get_default_async_client() -> AsyncTabstack:
    """Lazily construct and reuse a single default async client."""
    global _default_async_client
    if _default_async_client is None:
        _default_async_client = create_async_tabstack_client()
    return _default_async_client
