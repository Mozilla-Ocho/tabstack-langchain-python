"""Pydantic input schemas for the Tabstack tools.

These are the single source of truth for each tool's input surface and mirror
the TypeScript ``@tabstack/langchain`` and ``@tabstack/ai`` packages so the
cross-language story stays consistent.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal

__all__ = [
    "ExtractStructuredDataInput",
    "ExtractPageContentInput",
    "ResearchQuestionInput",
    "GenerateStructuredDataInput",
    "AutomateBrowserTaskInput",
]

_EFFORT_DESCRIPTION = (
    'Optional fetch effort: "min" (fastest), "standard" (default, balanced), '
    '"max" (full browser rendering for JS-heavy pages).'
)
_NOCACHE_DESCRIPTION = "Optional: bypass cache and force fresh retrieval"
_COUNTRY_DESCRIPTION = 'Optional ISO 3166-1 alpha-2 country code for geotargeting (e.g. "US")'


class ExtractStructuredDataInput(BaseModel):
    url: str = Field(description="URL to fetch and extract structured data from")
    json_schema_json: str = Field(
        description=(
            "A JSON-encoded JSON Schema object with concrete properties and descriptions "
            "for each field to extract."
        )
    )
    effort: Optional[Literal["min", "standard", "max"]] = Field(
        default=None, description=_EFFORT_DESCRIPTION
    )
    nocache: Optional[bool] = Field(default=None, description=_NOCACHE_DESCRIPTION)
    country: Optional[str] = Field(default=None, description=_COUNTRY_DESCRIPTION)


class ExtractPageContentInput(BaseModel):
    url: str = Field(description="URL to fetch and convert to clean markdown")
    effort: Optional[Literal["min", "standard", "max"]] = Field(
        default=None, description=_EFFORT_DESCRIPTION
    )
    nocache: Optional[bool] = Field(default=None, description=_NOCACHE_DESCRIPTION)
    country: Optional[str] = Field(default=None, description=_COUNTRY_DESCRIPTION)


class ResearchQuestionInput(BaseModel):
    query: str = Field(description="The research question to answer using multiple web sources")
    mode: Optional[Literal["fast", "balanced"]] = Field(
        default=None,
        description='Optional research mode: "fast" (quick) or "balanced" (default, more thorough)',
    )
    nocache: Optional[bool] = Field(default=None, description=_NOCACHE_DESCRIPTION)


class GenerateStructuredDataInput(BaseModel):
    url: str = Field(description="URL whose content should be fetched and transformed")
    instructions: str = Field(
        description="Natural-language instructions describing how to transform the page content"
    )
    json_schema_json: str = Field(
        description=(
            "A JSON-encoded JSON Schema object describing the shape of the generated output, "
            "with concrete properties and descriptions for each field."
        )
    )
    effort: Optional[Literal["min", "standard", "max"]] = Field(
        default=None, description=_EFFORT_DESCRIPTION
    )
    nocache: Optional[bool] = Field(default=None, description=_NOCACHE_DESCRIPTION)
    country: Optional[str] = Field(default=None, description=_COUNTRY_DESCRIPTION)


class AutomateBrowserTaskInput(BaseModel):
    task: str = Field(description="The browser automation task to perform, in natural language")
    url: Optional[str] = Field(default=None, description="Optional starting URL for the task")
    guardrails: Optional[str] = Field(
        default=None, description="Optional safety constraints on what the agent is allowed to do"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional JSON context data for form filling or complex tasks"
    )
    country: Optional[str] = Field(
        default=None,
        description='Optional ISO 3166-1 alpha-2 country code for geotargeted browsing (e.g. "US")',
    )
    max_iterations: Optional[int] = Field(
        default=None, description="Optional cap on the number of agent iterations"
    )
    max_validation_attempts: Optional[int] = Field(
        default=None, description="Optional cap on the number of result validation attempts"
    )
