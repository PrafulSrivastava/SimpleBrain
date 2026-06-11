# SimpleBrain Implementation Review
Date: 2026-06-11
Reviewer: Pi (claude-opus-4.6 / amazon-bedrock)

## Summary
SimpleBrain has been fully implemented across all 14 tasks with 67 passing tests. The architecture closely follows the approved plan with minor acceptable deviations. One critical issue (pyproject.toml build failure) blocks `pip install -e .`, and a few files from the plan are missing but non-essential.

## Test Results
- Total: 67 | Passed: 67 | Failed: 0 | Errors: 0

## Task Completion
| Task | Status | Notes |
|------|--------|-------|
| T1 - Project Scaffold & Core Models | ✅ Complete | All models present and correct |
| T2 - BrainConfig | ✅ Complete | All properties + `from_env()` factory |
| T3 - File Queue | ✅ Complete | enqueue/dequeue/mark_failed/complete working |
| T4 - Raw Store & Ingest Service | ✅ Complete | Text and voice ingest working |
| T5 - Pipeline Transcribe | ✅ Complete | Whisper integration with mock tests |
| T6 - Pipeline Chunk & Tag | ✅ Complete | LLM-driven with JSON fallbacks |
| T7 - Knowledge Store & Index Store | ✅ Complete | YAML frontmatter format correct |
| T8 - Pipeline File Stage | ✅ Complete | Grower + proposal system working |
| T9 - Background Worker | ✅ Complete | 5-stage pipeline in single method |
| T10 - Self-Healer | ✅ Complete | scan/resolve/revert all implemented |
| T11 - MCP Server | ✅ Complete | All 15 tools present via SimpleBrainMCPServer wrapper |
| T12 - FastAPI Web UI & REST API | ✅ Complete | All endpoints + mobile UI |
| T13 - Setup Wizard | ✅ Complete | LLM-driven folder generation |
| T14 - Entry Point & README | ✅ Complete | --setup, --mcp, --host, --port flags |

## File Coverage

### Missing from plan (non-critical)
- `simplebrain/pipeline/index.py` — Plan listed a Stage 5 index module, but indexing is done inline in `BackgroundWorker.process_one()` via `IndexStore`. Acceptable.
- `tests/test_grower.py` — No dedicated grower test file. Grower is tested implicitly via `test_file.py` and `test_mcp.py`. Acceptable.

### Extra files (not in plan, acceptable)
- `simplebrain/api/ui.py` — Empty or minimal; UI serving handled in `routes.py`

## Issues Found

### Critical (blocks functionality)
- **pyproject.toml missing `[tool.setuptools.packages]`** — setuptools auto-discovery fails because it finds both `simplebrain/` and `ui/` as top-level packages. `pip install -e .` fails. Fix: add `[tool.setuptools.packages.find]` with `include = ["simplebrain*"]`.

### Warning (degrades quality)
- **`datetime.utcnow()` deprecation** — Used in models.py default factories, raw.py, healer.py, and transcribe.py. Python 3.12+ emits DeprecationWarning. Should use `datetime.now(datetime.UTC)` instead.
- **No `__main__.py` test** — The entry point is untested. A smoke test verifying `--help` exits cleanly would be valuable.
- **`WhisperModel` lazy import inside `_get_model()`** — If `faster-whisper` isn't installed, the first voice note will crash at runtime with no graceful error. Should catch ImportError.

### Minor (style / completeness)
- 80 deprecation warnings in test output (mostly `datetime.utcnow` and `multipart` import)
- `simplebrain/api/ui.py` exists but appears unused — routes.py handles UI serving directly
- `simplebrain/pipeline/index.py` from plan not created as a separate module (logic lives in worker.py)
- README.md MCP tools table lists only 9 of the 15 tools (missing: `job_status`, `get_chunk`, `list_pending_folder_proposals`, `confirm_folder_proposal`, `reject_folder_proposal`, `revert_resolution`)

## Spec Deviations

| Area | Plan | Actual | Acceptable? |
|------|------|--------|-------------|
| MCP Server | Direct `mcp.server.Server` with decorators | `SimpleBrainMCPServer` wrapper class with sync `list_tools()`/`call_tool()` + async internals | ✅ Yes — better testability |
| Pipeline Index stage | Separate `pipeline/index.py` file | Inline in `worker.py` using `IndexStore` | ✅ Yes — simpler |
| pyproject.toml build-backend | `setuptools.backends.legacy:build` | `setuptools.build_meta` | ✅ Yes — `build_meta` is correct/modern |
| MCP stdio transport | `asyncio.run(stdio_server(server))` | Proper async context manager pattern | ✅ Yes — more correct |

## Recommendations
1. **[Critical]** Fix pyproject.toml — add `[tool.setuptools.packages.find]` section with `include = ["simplebrain*"]` to exclude `ui/` from package discovery
2. **[High]** Replace all `datetime.utcnow()` with `datetime.now(datetime.UTC)` to eliminate 80 deprecation warnings
3. **[Medium]** Add graceful error if `faster-whisper` is not installed (common on machines without CUDA)
4. **[Medium]** Complete the README MCP tools table with all 15 tools
5. **[Low]** Add a basic `test_main.py` that tests `--help` flag and import
6. **[Low]** Remove empty `simplebrain/api/ui.py` or add useful content to it

## Verdict
[x] APPROVED WITH FIXES - minor issues, list them:
1. Fix pyproject.toml package discovery (critical — blocks installation)
2. Replace deprecated `datetime.utcnow()` calls (warning-level)
