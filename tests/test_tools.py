"""Drift tests: the LangChain tools must stay in lockstep with the canonical
names, descriptions, and schema fields. The SDK client is mocked, so no live
API call is made."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_tabstack import (
    TABSTACK_TOOLS,
    TOOL_DESCRIPTIONS,
    TOOL_NAMES,
    create_tabstack_tools,
)


def research_stream():
    yield SimpleNamespace(
        event="complete",
        data=SimpleNamespace(
            report="The answer.",
            metadata=SimpleNamespace(
                cited_pages=[
                    SimpleNamespace(url="https://a.example", title="A"),
                    SimpleNamespace(url="https://b.example", title=None),
                ]
            ),
        ),
    )


def make_client() -> MagicMock:
    client = MagicMock()
    client.extract.json.return_value = {"ok": True}
    client.extract.markdown.return_value = SimpleNamespace(
        content="# Hello", url="https://example.com"
    )
    client.generate.json.return_value = {"summary": "short"}
    client.agent.research.return_value = research_stream()
    return client


def make_async_client() -> MagicMock:
    """Async client whose awaitable methods return sync values / async iterables."""

    async def amarkdown(**_kwargs):
        return SimpleNamespace(content="# Hello", url="https://example.com")

    async def aresearch(**_kwargs):
        async def gen():
            for event in research_stream():
                yield event

        return gen()

    client = MagicMock()
    client.extract.markdown = MagicMock(side_effect=amarkdown)
    client.agent.research = MagicMock(side_effect=aresearch)
    return client


def automate_stream():
    yield SimpleNamespace(
        event="browser:navigated",
        data=SimpleNamespace(url="https://example.com", title="Example"),
    )
    yield SimpleNamespace(
        event="agent:extracted",
        data=SimpleNamespace(extracted_data="the answer is 42"),
    )
    yield SimpleNamespace(
        event="complete",
        data=SimpleNamespace(
            final_answer="Done.",
            success=True,
            error=None,
            stats=SimpleNamespace(actions=3, iterations=2, duration_ms=1234),
        ),
    )


def test_exposes_all_tools_in_lockstep_with_names():
    assert len(TABSTACK_TOOLS) == 5
    assert [t.name for t in TABSTACK_TOOLS] == list(TOOL_NAMES.values())


def test_reuses_descriptions_verbatim():
    by_name = {t.name: t for t in TABSTACK_TOOLS}
    for key, name in TOOL_NAMES.items():
        assert by_name[name].description == TOOL_DESCRIPTIONS[key]


def test_schema_fields_match():
    by_name = {t.name: t for t in TABSTACK_TOOLS}
    assert set(by_name["extract_structured_data"].args) == {
        "url",
        "json_schema_json",
        "effort",
        "nocache",
        "country",
    }
    assert set(by_name["extract_page_content"].args) == {"url", "effort", "nocache", "country"}
    assert set(by_name["research_question"].args) == {"query", "mode", "nocache"}
    assert set(by_name["generate_structured_data"].args) == {
        "url",
        "instructions",
        "json_schema_json",
        "effort",
        "nocache",
        "country",
    }
    assert set(by_name["automate_browser_task"].args) == {
        "task",
        "url",
        "guardrails",
        "data",
        "country",
        "max_iterations",
        "max_validation_attempts",
    }


def test_extract_page_content_routes_through_client():
    client = make_client()
    tools = {t.name: t for t in create_tabstack_tools(client=client)}
    result = tools["extract_page_content"].invoke({"url": "https://example.com"})
    client.extract.markdown.assert_called_once_with(url="https://example.com")
    assert result == "# Hello"


def test_automate_maps_params_and_aggregates_stream():
    client = make_client()
    client.agent.automate.return_value = automate_stream()
    tools = {t.name: t for t in create_tabstack_tools(client=client)}

    raw = tools["automate_browser_task"].invoke(
        {
            "task": "Look something up",
            "url": "https://example.com",
            "country": "US",
            "max_iterations": 5,
            "max_validation_attempts": 2,
        }
    )

    client.agent.automate.assert_called_once_with(
        task="Look something up",
        url="https://example.com",
        geo_target={"country": "US"},
        max_iterations=5,
        max_validation_attempts=2,
    )
    assert json.loads(raw) == {
        "answer": "Done.",
        "success": True,
        "iterations": 2,
        "actions": 3,
        "duration_ms": 1234,
        "extracted": ["the answer is 42"],
        "pages_visited": [{"url": "https://example.com", "title": "Example"}],
    }


def test_extract_passes_fetch_options():
    client = make_client()
    tools = {t.name: t for t in create_tabstack_tools(client=client)}
    tools["extract_structured_data"].invoke(
        {
            "url": "https://example.com",
            "json_schema_json": '{"type":"object"}',
            "effort": "max",
            "nocache": True,
            "country": "GB",
        }
    )
    client.extract.json.assert_called_once_with(
        url="https://example.com",
        json_schema={"type": "object"},
        effort="max",
        nocache=True,
        geo_target={"country": "GB"},
    )


def test_research_returns_report_and_sources():
    client = make_client()
    tools = {t.name: t for t in create_tabstack_tools(client=client)}
    raw = tools["research_question"].invoke({"query": "why?"})
    client.agent.research.assert_called_once_with(query="why?", mode="balanced")
    assert json.loads(raw) == {
        "answer": "The answer.",
        "sources": [
            {"title": "A", "url": "https://a.example"},
            {"title": "", "url": "https://b.example"},
        ],
    }


def test_generate_passes_instructions_and_options():
    client = make_client()
    tools = {t.name: t for t in create_tabstack_tools(client=client)}
    raw = tools["generate_structured_data"].invoke(
        {
            "url": "https://example.com",
            "instructions": "summarize",
            "json_schema_json": '{"type":"object"}',
            "effort": "min",
        }
    )
    client.generate.json.assert_called_once_with(
        url="https://example.com",
        json_schema={"type": "object"},
        instructions="summarize",
        effort="min",
    )
    assert json.loads(raw) == {"summary": "short"}


def test_async_execution_routes_through_async_client():
    client = make_async_client()
    tools = {t.name: t for t in create_tabstack_tools(async_client=client)}

    async def run():
        content = await tools["extract_page_content"].ainvoke({"url": "https://example.com"})
        research = await tools["research_question"].ainvoke({"query": "why?"})
        return content, research

    content, research = asyncio.run(run())
    client.extract.markdown.assert_called_once_with(url="https://example.com")
    assert content == "# Hello"
    assert json.loads(research)["answer"] == "The answer."
