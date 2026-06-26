# AGENTS.md: langchain-tabstack

Guide for AI agents working on this package. Humans: see `README.md`.

## What this package is

Tabstack tools for LangChain (Python). It wraps the official `tabstack` SDK and exposes Tabstack's
extract / research / generate / automate capabilities as native LangChain tools. It mirrors the
TypeScript `@tabstack/langchain` and `@tabstack/ai` packages tool-for-tool: same names, descriptions,
and input fields.

## Why use it

Schema-enforced web extraction and multi-source research as drop-in LangChain tools, backed by the
SDK (no bespoke HTTP, no Playwright). Consistent with the TypeScript packages so a cross-language
stack behaves the same.

## How to use it (consumer)

```python
from langchain_tabstack import TABSTACK_TOOLS, create_tabstack_tools

# TABSTACK_TOOLS: list using the default client (reads TABSTACK_API_KEY lazily)
# create_tabstack_tools(api_key=...) or (client=...) / (async_client=...) for a custom client
```

Every tool supports both `invoke` (sync) and `ainvoke` (native async via `AsyncTabstack`).

## Architecture (single source of truth, mirror of the TS `core`)

| File | Responsibility |
| --- | --- |
| `client.py` | Sync + async client construction, lazy defaults (read `TABSTACK_API_KEY`). |
| `schemas.py` | Pydantic input models. Single source of truth for the input surface. |
| `tools.py` | Tool names/descriptions, sync + async bodies, the `create_tabstack_tools` factory. |
| `errors.py` | `TabstackToolError` + `normalize_error`. |

## Rules specific to this package

- **Python 3.9 is the floor.** Use `typing.Optional/Dict/List`, not PEP 604/585 (`X | None`,
  `list[...]`). Pydantic evaluates these annotations at runtime and the newer syntax breaks on 3.9.
  This is why ruff's `UP` rules are disabled in `pyproject.toml`.
- All network work goes through the SDK client. No bespoke HTTP.
- Tools return **JSON strings** (`json.dumps`), the LangChain-Python convention. `extract_page_content`
  returns the markdown string directly. Keys are snake_case (the TS packages use camelCase objects).
- `automate_browser_task` runs non-interactively: it does not enable the human-in-the-loop
  `agent.automate_input` flow.
- Keep names, descriptions, and fields in lockstep with the TypeScript packages.

## Adding a tool

1. `schemas.py`: pydantic input model (reuse the shared field-description constants).
2. `tools.py`: `TOOL_NAMES`, `TOOL_DESCRIPTIONS`, a sync body, an async body, and `_build(...)` in
   `create_tabstack_tools`.
3. `__init__.py`: export anything new.
4. Add tests, and mirror the tool into the TypeScript packages.

## Build / test

```bash
python -m venv .venv
.venv/bin/pip install -e ".[test,dev]"
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest -q
.venv/bin/python -m build          # wheel + sdist
```

Tests mock the SDK client (sync via `MagicMock`, async via coroutine side-effects) and assert names,
descriptions, schema fields, and execution routing, so drift fails CI. CI runs the matrix
3.9 / 3.10 / 3.11 / 3.12.
