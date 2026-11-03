# langchain-tabstack

Give your [LangChain](https://python.langchain.com) agents reliable web access. Schema-enforced
extraction, multi-source research, AI transformation, and browser automation, all as native
LangChain tools backed by the official [Tabstack SDK](https://pypi.org/project/tabstack/).

## Why Tabstack

LangChain's built-in loaders (`WebBaseLoader`, `PlaywrightURLLoader`) are fine for prototypes and
brittle in production: unpredictable parsing, Playwright binaries to install and maintain, and
behaviour that drifts across LangChain releases.

Tabstack replaces them with a hosted API:

- **Schema-enforced output.** You define the shape, you get that shape back. No prompt-engineering
  the JSON out of raw text.
- **No browser to run.** JS-heavy pages render server-side. No Playwright, no binaries.
- **Version-independent.** It is an SDK call, not a loader coupled to your LangChain version.
- **Sync and async.** Every tool supports `invoke` and native `ainvoke`.

## Install

```bash
pip install langchain-tabstack
```

Requires Python 3.9+. For the agent example below you also need a chat model, for example
`pip install langchain langchain-openai`. Set your API key (get one at
[console.tabstack.ai](https://console.tabstack.ai)):

```bash
export TABSTACK_API_KEY="your-key-here"
```

## Quickstart

```python
from langchain.agents import create_agent
from langchain_tabstack import TABSTACK_TOOLS

agent = create_agent(
    "openai:gpt-4o",
    tools=TABSTACK_TOOLS,
    system_prompt=(
        "You are a research assistant with web intelligence tools. "
        "Use extract_structured_data for specific fields from a URL, "
        "extract_page_content for full page text, and research_question for multi-source research."
    ),
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What are Vercel's pricing plans?"}]}
)
print(result["messages"][-1].content)
```

`TABSTACK_TOOLS` reads `TABSTACK_API_KEY` from the environment and is ready to drop into any agent.

> Using LangChain 0.x? `create_agent` is the LangChain 1.x replacement for `AgentExecutor` +
> `create_tool_calling_agent`. The tools themselves work with either.

## The tools

| Tool | What it does |
| --- | --- |
| `extract_structured_data` | Pull specific fields from a URL into a JSON shape you define. |
| `extract_page_content` | Fetch a page as clean markdown. |
| `research_question` | Synthesised answer with cited sources across multiple pages. |
| `generate_structured_data` | Fetch a page, then AI-transform it into derived or reshaped JSON. |
| `automate_browser_task` | Run a multi-step, natural-language browser task. |

Every tool is exported individually too, so you can use one directly without an agent. Tools return
a JSON string (use `json.loads`); `extract_page_content` returns markdown text directly.

### extract_structured_data

```python
import json
from langchain_tabstack import extract_structured_data_tool

raw = extract_structured_data_tool.invoke(
    {
        "url": "https://news.ycombinator.com",
        # json_schema_json is a JSON-encoded JSON Schema describing the fields you want.
        "json_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "stories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "points": {"type": "number", "description": "Story points"},
                            },
                        },
                    }
                },
            }
        ),
    }
)
data = json.loads(raw)
print(data["stories"])
```

### extract_page_content

```python
from langchain_tabstack import extract_page_content_tool

markdown = extract_page_content_tool.invoke({"url": "https://example.com/blog/article"})
```

### research_question

```python
import json
from langchain_tabstack import research_question_tool

result = json.loads(
    research_question_tool.invoke(
        {"query": "What are the latest developments in quantum error correction?"}
    )
)
print(result["answer"])
for source in result["sources"]:  # [{"title": ..., "url": ...}, ...]
    print(source["url"])
```

### generate_structured_data

```python
import json
from langchain_tabstack import generate_structured_data_tool

raw = generate_structured_data_tool.invoke(
    {
        "url": "https://news.ycombinator.com",
        "instructions": "For each story, categorize it and write a one-sentence summary.",
        "json_schema_json": json.dumps(
            {
                "type": "object",
                "properties": {
                    "summaries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "category": {"type": "string"},
                                "summary": {"type": "string"},
                            },
                        },
                    }
                },
            }
        ),
    }
)
```

### automate_browser_task

```python
import json
from langchain_tabstack import automate_browser_task_tool

result = json.loads(
    automate_browser_task_tool.invoke(
        {
            "task": "Find the top 3 trending repositories and their star counts",
            "url": "https://github.com/trending",
            "guardrails": "browse and extract only, do not submit forms",
        }
    )
)
# {"answer", "success", "iterations", "actions", "duration_ms", "extracted", "pages_visited"}
```

## Optional inputs

Pass these alongside the required inputs for finer control. They are sent only when provided, so
omitting them keeps Tabstack's defaults.

- `extract_structured_data`, `extract_page_content`, `generate_structured_data`:
  - `effort`: `"min"` | `"standard"` | `"max"`. Use `"max"` for JS-heavy pages (full server-side
    browser rendering, the `PlaywrightURLLoader` replacement).
  - `nocache`: `True` to bypass the cache.
  - `country`: ISO 3166-1 alpha-2 code (for example `"US"`) for geotargeted fetches.
- `research_question`:
  - `mode`: `"fast"` (default) | `"balanced"`. `"balanced"` is more thorough and needs a Team or
    Pro plan.
  - `nocache`: `True` to bypass the cache.
- `automate_browser_task`: `data` (context for form filling), `country`, `max_iterations`,
  `max_validation_attempts`.

```python
# Render a JS-heavy SPA, fresh, from the UK:
extract_page_content_tool.invoke({"url": url, "effort": "max", "nocache": True, "country": "GB"})
```

## Async

Every tool supports `ainvoke` natively, backed by `AsyncTabstack`, so it runs in your event loop
without a thread-pool bounce:

```python
markdown = await extract_page_content_tool.ainvoke({"url": "https://example.com"})
```

## Configuration

For a custom API key or base URL, or to reuse one client, build the tools explicitly:

```python
from langchain_tabstack import create_tabstack_tools

tools = create_tabstack_tools(api_key="...")
# or pass clients you already have:
# create_tabstack_tools(client=..., async_client=...)
```

## Error handling

Tool calls raise `TabstackToolError` with a normalised message and, for API failures, an HTTP
`status`:

```python
from langchain_tabstack import TabstackToolError, extract_page_content_tool

try:
    extract_page_content_tool.invoke({"url": "https://example.com"})
except TabstackToolError as err:
    print(f"Tabstack failed ({err.status or 'no status'}): {err}")
```

## Good to know

- **`automate_browser_task` runs non-interactively.** It does not pause for human-in-the-loop form
  input, so it never blocks. It returns the final answer plus the data it extracted and the pages it
  visited.
- The client is created lazily, so importing the package never requires an API key to be set.
- The tool names, descriptions, and inputs match the
  [`@tabstack/langchain`](https://www.npmjs.com/package/@tabstack/langchain) (LangChain.js) and
  [`@tabstack/ai`](https://www.npmjs.com/package/@tabstack/ai) (Vercel AI SDK) packages, so
  behaviour is consistent across languages and frameworks. Those return native objects with
  camelCase keys; this package returns JSON strings with snake_case keys, the LangChain-Python
  convention. The data is the same.

## Links

- [Tabstack docs](https://docs.tabstack.ai)
- [Tabstack SDK (`tabstack`)](https://pypi.org/project/tabstack/)
- [Get an API key](https://console.tabstack.ai)
