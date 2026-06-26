"""Normalised error surfaced consistently by the Tabstack tools."""

from __future__ import annotations

from typing import Any, Optional

from tabstack import APIError, APIStatusError

__all__ = ["TabstackToolError", "normalize_error"]


class TabstackToolError(Exception):
    """A small normalised error wrapping the SDK's exceptions.

    Consumers can catch this without depending on SDK internals.
    """

    def __init__(self, message: str, *, status: Optional[int] = None, cause: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.__cause__ = cause if isinstance(cause, BaseException) else None
        self.cause = cause


def normalize_error(err: Any) -> TabstackToolError:
    """Map any raised value into a :class:`TabstackToolError`."""
    if isinstance(err, TabstackToolError):
        return err
    if isinstance(err, APIStatusError):
        return TabstackToolError(str(err), status=err.status_code, cause=err)
    if isinstance(err, APIError):
        return TabstackToolError(str(err), cause=err)
    if isinstance(err, Exception):
        return TabstackToolError(str(err), cause=err)
    return TabstackToolError("Unknown Tabstack error", cause=err)
