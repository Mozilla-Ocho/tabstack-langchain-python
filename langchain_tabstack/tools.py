"""Framework-agnostic Tabstack tool bodies plus the LangChain tool factory.

The tool names and descriptions are the single source of truth, kept in lockstep
with the TypeScript ``@tabstack/langchain`` and ``@tabstack/ai`` packages. Each
tool is exposed with both a synchronous implementation and a native async
coroutine, so ``invoke`` and ``ainvoke`` both run without a thread-pool bounce.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool
from tabstack import AsyncTabstack, Tabstack

from .client import get_default_async_client, get_default_client
from .errors import normalize_error
from .schemas import (
    AutomateBrowserTaskInput,
    ExtractPageContentInput,
    ExtractStructuredDataInput,
    GenerateStructuredDataInput,
    ResearchQuestionInput,
)

__all__ = [
    "TOOL_NAMES",
    "TOOL_DESCRIPTIONS",
    "extract_structured_data",
    "extract_page_content",
    "research_question",
    "generate_structured_data",
    "automate_browser_task",
    "create_tabstack_tools",
]

TOOL_NAMES = {
    "extract_structured_data": "extract_structured_data",
    "extract_page_content": "extract_page_content",
    "research_question": "research_question",
    "generate_structured_data": "generate_structured_data",
    "automate_browser_task": "automate_browser_task",
}

TOOL_DESCRIPTIONS = {
    "extract_structured_data": (
        "Extract structured JSON data from a URL. Use when you need specific fields from a web "
        "page. 'json_schema_json' must be a JSON-encoded JSON Schema object with concrete "
        "properties and descriptions for each field to extract. See the schema-design guide for "
        "patterns that produce reliable results. Returns the extracted data as JSON."
    ),
    "extract_page_content": (
        "Fetch a URL and return its content as clean markdown. Use when you need to read a page's "
        "full content for summarization or when you don't know what specific fields to extract. "
        "Returns clean markdown text."
    ),
    "research_question": (
        "Research a question using multiple web sources. Use when you need a synthesized answer "
        "from multiple sources, not just data from a single known page. Returns an answer with "
        "cited sources."
    ),
    "generate_structured_data": (
        "Fetch a URL, then transform and restructure its content with AI into structured JSON. "
        "Use when you need derived or reshaped data (summaries, categorizations, computed "
        "fields), not just verbatim extraction. 'instructions' tells the AI how to transform the "
        "content; 'json_schema_json' must be a JSON-encoded JSON Schema object describing the "
        "output shape. Returns the generated data as JSON."
    ),
    "automate_browser_task": (
        "Run an AI browser automation task described in natural language. Use for multi-step web "
        "workflows: navigating, filling forms, gathering, and extracting across pages. Provide a "
        "clear 'task' and optionally a starting 'url', 'guardrails' to constrain the agent, "
        "'data' as context for form filling, a 'country' code for geotargeted browsing, and caps "
        "via 'max_iterations' and 'max_validation_attempts'. Runs non-interactively and returns "
        "the final answer plus any extracted data and the pages visited."
    ),
}


def _fetch_options(inp: Any) -> Dict[str, Any]:
    """Shared fetch options (effort, cache bypass, geotargeting) for the extract
    and generate endpoints. Omitted values fall back to SDK defaults."""
    options: Dict[str, Any] = {}
    if inp.effort is not None:
        options["effort"] = inp.effort
    if inp.nocache is not None:
        options["nocache"] = inp.nocache
    if inp.country is not None:
        options["geo_target"] = {"country": inp.country}
    return options


def _research_kwargs(inp: ResearchQuestionInput) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"query": inp.query, "mode": inp.mode or "balanced"}
    if inp.nocache is not None:
        kwargs["nocache"] = inp.nocache
    return kwargs


def _automate_kwargs(inp: AutomateBrowserTaskInput) -> Dict[str, Any]:
    # Interactive mode is intentionally left off: a one-shot tool cannot service
    # the human-in-the-loop form-data callback (``agent.automate_input``).
    kwargs: Dict[str, Any] = {"task": inp.task}
    if inp.url is not None:
        kwargs["url"] = inp.url
    if inp.guardrails is not None:
        kwargs["guardrails"] = inp.guardrails
    if inp.data is not None:
        kwargs["data"] = inp.data
    if inp.country is not None:
        kwargs["geo_target"] = {"country": inp.country}
    if inp.max_iterations is not None:
        kwargs["max_iterations"] = inp.max_iterations
    if inp.max_validation_attempts is not None:
        kwargs["max_validation_attempts"] = inp.max_validation_attempts
    return kwargs


def _research_complete(event: Any) -> Dict[str, Any]:
    cited = event.data.metadata.cited_pages or []
    return {
        "answer": event.data.report,
        "sources": [{"title": page.title or "", "url": page.url} for page in cited],
    }


def _automate_complete(
    event: Any, extracted: List[str], pages_visited: List[Dict[str, str]]
) -> Dict[str, Any]:
    data = event.data
    if not data.success and data.error:
        raise RuntimeError(f"Automation failed: {data.error.message}")
    return {
        "answer": data.final_answer,
        "success": data.success,
        "iterations": data.stats.iterations,
        "actions": data.stats.actions,
        "duration_ms": data.stats.duration_ms,
        "extracted": extracted,
        "pages_visited": pages_visited,
    }


def _automate_incomplete(
    extracted: List[str], pages_visited: List[Dict[str, str]]
) -> Dict[str, Any]:
    return {
        "answer": None,
        "success": False,
        "iterations": 0,
        "actions": 0,
        "duration_ms": 0,
        "extracted": extracted,
        "pages_visited": pages_visited,
    }


# --- Synchronous tool bodies -------------------------------------------------


def extract_structured_data(inp: ExtractStructuredDataInput, client: Tabstack) -> Dict[str, Any]:
    """Extract structured data from a URL via ``client.extract.json``."""
    try:
        schema = json.loads(inp.json_schema_json)
        return client.extract.json(url=inp.url, json_schema=schema, **_fetch_options(inp))
    except Exception as err:
        raise normalize_error(err) from err


def extract_page_content(inp: ExtractPageContentInput, client: Tabstack) -> str:
    """Fetch a URL and return clean markdown via ``client.extract.markdown``."""
    try:
        result = client.extract.markdown(url=inp.url, **_fetch_options(inp))
        return result.content
    except Exception as err:
        raise normalize_error(err) from err


def research_question(inp: ResearchQuestionInput, client: Tabstack) -> Dict[str, Any]:
    """Research a question across multiple web sources via ``client.agent.research``."""
    try:
        stream = client.agent.research(**_research_kwargs(inp))
        for event in stream:
            if event.event == "error":
                message = getattr(event.data, "message", None) or "unknown error"
                raise RuntimeError(f"Research failed: {message}")
            if event.event == "complete":
                return _research_complete(event)
        return {"answer": "Research did not complete", "sources": []}
    except Exception as err:
        raise normalize_error(err) from err


def generate_structured_data(inp: GenerateStructuredDataInput, client: Tabstack) -> Dict[str, Any]:
    """Fetch a URL and AI-transform its content via ``client.generate.json``."""
    try:
        schema = json.loads(inp.json_schema_json)
        return client.generate.json(
            url=inp.url,
            json_schema=schema,
            instructions=inp.instructions,
            **_fetch_options(inp),
        )
    except Exception as err:
        raise normalize_error(err) from err


def automate_browser_task(inp: AutomateBrowserTaskInput, client: Tabstack) -> Dict[str, Any]:
    """Run a browser automation task via ``client.agent.automate``.

    Consumes the SSE stream non-interactively and returns the final answer plus
    any extracted data and the pages visited.
    """
    try:
        stream = client.agent.automate(**_automate_kwargs(inp))
        extracted: List[str] = []
        pages_visited: List[Dict[str, str]] = []
        for event in stream:
            if event.event == "agent:extracted":
                extracted.append(event.data.extracted_data)
            elif event.event == "browser:navigated":
                pages_visited.append({"url": event.data.url, "title": event.data.title})
            elif event.event == "error":
                raise RuntimeError(f"Automation failed: {event.data.error.message}")
            elif event.event == "complete":
                return _automate_complete(event, extracted, pages_visited)
        return _automate_incomplete(extracted, pages_visited)
    except Exception as err:
        raise normalize_error(err) from err


# --- Asynchronous tool bodies ------------------------------------------------


async def aextract_structured_data(
    inp: ExtractStructuredDataInput, client: AsyncTabstack
) -> Dict[str, Any]:
    try:
        schema = json.loads(inp.json_schema_json)
        return await client.extract.json(url=inp.url, json_schema=schema, **_fetch_options(inp))
    except Exception as err:
        raise normalize_error(err) from err


async def aextract_page_content(inp: ExtractPageContentInput, client: AsyncTabstack) -> str:
    try:
        result = await client.extract.markdown(url=inp.url, **_fetch_options(inp))
        return result.content
    except Exception as err:
        raise normalize_error(err) from err


async def aresearch_question(inp: ResearchQuestionInput, client: AsyncTabstack) -> Dict[str, Any]:
    try:
        stream = await client.agent.research(**_research_kwargs(inp))
        async for event in stream:
            if event.event == "error":
                message = getattr(event.data, "message", None) or "unknown error"
                raise RuntimeError(f"Research failed: {message}")
            if event.event == "complete":
                return _research_complete(event)
        return {"answer": "Research did not complete", "sources": []}
    except Exception as err:
        raise normalize_error(err) from err


async def agenerate_structured_data(
    inp: GenerateStructuredDataInput, client: AsyncTabstack
) -> Dict[str, Any]:
    try:
        schema = json.loads(inp.json_schema_json)
        return await client.generate.json(
            url=inp.url,
            json_schema=schema,
            instructions=inp.instructions,
            **_fetch_options(inp),
        )
    except Exception as err:
        raise normalize_error(err) from err


async def aautomate_browser_task(
    inp: AutomateBrowserTaskInput, client: AsyncTabstack
) -> Dict[str, Any]:
    try:
        stream = await client.agent.automate(**_automate_kwargs(inp))
        extracted: List[str] = []
        pages_visited: List[Dict[str, str]] = []
        async for event in stream:
            if event.event == "agent:extracted":
                extracted.append(event.data.extracted_data)
            elif event.event == "browser:navigated":
                pages_visited.append({"url": event.data.url, "title": event.data.title})
            elif event.event == "error":
                raise RuntimeError(f"Automation failed: {event.data.error.message}")
            elif event.event == "complete":
                return _automate_complete(event, extracted, pages_visited)
        return _automate_incomplete(extracted, pages_visited)
    except Exception as err:
        raise normalize_error(err) from err


def _dumps(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def create_tabstack_tools(
    client: Optional[Tabstack] = None,
    *,
    async_client: Optional[AsyncTabstack] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> List[BaseTool]:
    """Build the Tabstack LangChain tools.

    Pass a ready ``client`` / ``async_client``, or ``api_key`` / ``base_url`` to
    construct them. When nothing is given, each tool resolves the lazily-built
    default client at call time, so building the tools never requires an API key.
    Both sync (``invoke``) and async (``ainvoke``) execution are supported.

    Returns:
        A list of LangChain tools ready to pass to ``create_agent`` /
        ``AgentExecutor``.
    """
    if api_key is not None or base_url is not None:
        from .client import create_async_tabstack_client, create_tabstack_client

        if client is None:
            client = create_tabstack_client(api_key=api_key, base_url=base_url)
        if async_client is None:
            async_client = create_async_tabstack_client(api_key=api_key, base_url=base_url)

    def sync() -> Tabstack:
        return client if client is not None else get_default_client()

    def asyncc() -> AsyncTabstack:
        return async_client if async_client is not None else get_default_async_client()

    def _build(name: str, schema, body, abody) -> StructuredTool:
        def func(**kwargs: Any) -> str:
            return _dumps(body(schema(**kwargs), sync()))

        async def coroutine(**kwargs: Any) -> str:
            return _dumps(await abody(schema(**kwargs), asyncc()))

        return StructuredTool.from_function(
            func=func,
            coroutine=coroutine,
            name=TOOL_NAMES[name],
            description=TOOL_DESCRIPTIONS[name],
            args_schema=schema,
        )

    return [
        _build(
            "extract_structured_data",
            ExtractStructuredDataInput,
            extract_structured_data,
            aextract_structured_data,
        ),
        _build(
            "extract_page_content",
            ExtractPageContentInput,
            extract_page_content,
            aextract_page_content,
        ),
        _build(
            "research_question",
            ResearchQuestionInput,
            research_question,
            aresearch_question,
        ),
        _build(
            "generate_structured_data",
            GenerateStructuredDataInput,
            generate_structured_data,
            agenerate_structured_data,
        ),
        _build(
            "automate_browser_task",
            AutomateBrowserTaskInput,
            automate_browser_task,
            aautomate_browser_task,
        ),
    ]
