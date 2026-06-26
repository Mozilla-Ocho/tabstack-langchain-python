"""Tabstack tools for LangChain.

Schema-enforced web extraction and research, backed by the official Tabstack SDK.
"""

from __future__ import annotations

from .client import (
    create_async_tabstack_client,
    create_tabstack_client,
    get_default_async_client,
    get_default_client,
)
from .errors import TabstackToolError, normalize_error
from .schemas import (
    AutomateBrowserTaskInput,
    ExtractPageContentInput,
    ExtractStructuredDataInput,
    GenerateStructuredDataInput,
    ResearchQuestionInput,
)
from .tools import (
    TOOL_DESCRIPTIONS,
    TOOL_NAMES,
    create_tabstack_tools,
)

# Default-client tools. The client is resolved lazily on first tool call, so
# importing this module never requires TABSTACK_API_KEY to be set.
TABSTACK_TOOLS = create_tabstack_tools()
(
    extract_structured_data_tool,
    extract_page_content_tool,
    research_question_tool,
    generate_structured_data_tool,
    automate_browser_task_tool,
) = TABSTACK_TOOLS

# Alias matching the common LangChain naming convention.
get_tabstack_tools = create_tabstack_tools

__all__ = [
    "create_tabstack_tools",
    "get_tabstack_tools",
    "TABSTACK_TOOLS",
    "extract_structured_data_tool",
    "extract_page_content_tool",
    "research_question_tool",
    "generate_structured_data_tool",
    "automate_browser_task_tool",
    "create_tabstack_client",
    "create_async_tabstack_client",
    "get_default_client",
    "get_default_async_client",
    "TabstackToolError",
    "normalize_error",
    "TOOL_NAMES",
    "TOOL_DESCRIPTIONS",
    "ExtractStructuredDataInput",
    "ExtractPageContentInput",
    "ResearchQuestionInput",
    "GenerateStructuredDataInput",
    "AutomateBrowserTaskInput",
]

__version__ = "0.1.0"
