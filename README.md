# SimpleBrain

A self-organising, self-growing, and self-healing second brain.

Drop voice or text notes — SimpleBrain transcribes, chunks, tags, and files them
automatically using an LLM pipeline. Knowledge is stored as human-readable Markdown
files with YAML frontmatter. The brain exposes a full REST API, a mobile web UI,
and an MCP server for AI tool integration.

---

## Features

- **Voice + Text Ingest** — instant queueing, async pipeline processing
- **5-Stage Pipeline** — Transcribe → Chunk → Tag → File → Index
- **Single-Question Setup** — describe your brain in plain English; LLM designs the folder structure
- **Human-Readable Filenames** — chunks saved as `title-slug-{id}.md`, not bare UUIDs
- **Self-Organising** — LLM proposes and creates new folders as knowledge grows
- **Self-Healing** — detects factual conflicts, structural issues, and topic pivots
- **MCP Server** — 15 tools for Claude Desktop / MCP CLI integration
- **Mobile Web UI** — tap-to-record + text input, optimised for iPhone Safari
- **Human-Readable Storage** — all knowledge as `.md` files, fully portable
- **All LLM Config via `.env`** — no provider questions at runtime; supports openai, anthropic, ollama, lmstudio, groq, gemini, cohere

---

## Quickstart

```bash
# 1. Install
pip install -e .

# 2. Configure your LLM (no questions asked at runtime)
cp .env.example .env
# Edit .env: set LLM_PROVIDER, LLM_MODEL, and your API key (or point at LM Studio / Ollama)

# 3. First-time setup — one question, LLM designs your folder structure
simplebrain --setup

# 4. Run the brain (API server + background worker)
simplebrain

# 5. Run as MCP server for Claude Desktop / MCP CLI
simplebrain --mcp
```

`python -m simplebrain` works identically to `simplebrain` everywhere.

---

## CLI Flags

| Flag | Description |
|---|---|
| *(none)* | Start API server + background pipeline worker |
| `--setup` | Run the setup wizard (one question, LLM proposes folder structure) |
| `--mcp` | Start as MCP stdio server |
| `--dir PATH` | Override the brain root directory (overrides `BRAIN_ROOT` in `.env`) |
| `--host HOST` | API bind host (default: `0.0.0.0`) |
| `--port PORT` | API port (default: `8000`) |

### Examples

```bash
# Set up a brain in a specific directory
simplebrain --setup --dir ~/work-brain

# Run a different brain on a different port
simplebrain --dir ~/personal-brain --port 8001

# Relative and tilde paths both work
simplebrain --setup --dir ./brain
```

---

## Setup Wizard

Run `simplebrain --setup` (optionally with `--dir`) and describe your knowledge base
in your own words — no separate questions for LLM provider, model, schedule, or topics.
Everything is driven by your `.env` file and the description you provide.

```
  SimpleBrain Setup
  --------------------------------------------------
  Provider : lmstudio
  Model    : lm_studio/google/gemma-4-e2b
  API base : http://localhost:1234/v1
  Supported: openai | anthropic | ollama | lmstudio | groq | gemini | cohere
  Brain dir: /Users/alice/work-brain

  Describe your knowledge base in your own words.
  Include: what it's for, who will use it, what topics or areas
  you plan to store, and anything else that would help organise it.
  (End input with a blank line)

  > I'm a software engineer tracking projects, book learnings,
  > meeting notes, and architecture decisions.
  >

  Thinking...

  Proposed Knowledge Base
  --------------------------------------------------
  Purpose : A personal second brain for a software engineer.
  Healing : daily

  Folder                 Description
  ------                 -----------
  projects               Notes and status for each active project.
  learnings              Insights from books, courses, and talks.
  meetings               Meeting notes and action items.
  decisions              Architecture and technical decision records.
  research               Deep dives and reference material.
  archive                Old or inactive content.

  Create this structure? [Y/n]
```

The LLM proposes folder names, descriptions, and a README for each folder.
Nothing is written to disk until you confirm.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

```bash
# Storage
BRAIN_ROOT=~/simplebrain        # Where to store the brain
BRAIN_USER=default              # Written into every chunk's frontmatter
BRAIN_DEVICE=mac                # Device label (useful across multiple machines)
BRAIN_HEALER_SCHEDULE=daily     # daily | weekly | manual

# LLM (pick one provider block)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

### Supported Providers

| Provider | `LLM_PROVIDER` | API Key Needed |
|---|---|---|
| OpenAI | `openai` | Yes — `OPENAI_API_KEY` |
| Anthropic | `anthropic` | Yes — `ANTHROPIC_API_KEY` |
| LM Studio | `lmstudio` | No — set `LLM_API_BASE` to your server URL |
| Ollama | `ollama` | No |
| Groq | `groq` | Yes — `GROQ_API_KEY` |
| Google Gemini | `gemini` | Yes — `GEMINI_API_KEY` |
| Cohere | `cohere` | Yes — `COHERE_API_KEY` |

See `.env.example` for per-provider example blocks.

---

## iPhone / Mobile Access

1. Run `simplebrain` on your Mac
2. Open `http://<your-mac-ip>:8000` in Safari on your iPhone
3. **Add to Home Screen** for instant native-app-like access
4. Tap the microphone to record a voice note, or type in the text box

---

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/status` | Queue depth, pending conflicts, pending proposals |
| `POST` | `/notes/text` | Add a text note |
| `POST` | `/notes/voice` | Add a voice note (base64 audio) |
| `GET` | `/topics` | List topics with chunk counts |
| `GET` | `/tags` | List tags with usage counts |
| `GET` | `/search?query=...` | Search knowledge base by tag keywords |
| `GET` | `/chunks/{id}` | Get a specific chunk |
| `GET` | `/proposals` | List pending folder proposals |
| `POST` | `/proposals/{id}/confirm` | Confirm a new folder |
| `POST` | `/proposals/{id}/reject` | Reject a folder proposal |
| `GET` | `/conflicts` | List pending conflicts |
| `POST` | `/conflicts/{id}/resolve` | Resolve a conflict |
| `POST` | `/conflicts/{id}/revert` | Revert a resolution |
| `POST` | `/heal` | Trigger a healing scan |
| `GET` | `/docs` | Interactive API docs (Swagger UI) |

---

## MCP Tools

Configure in Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "simplebrain": {
      "command": "python",
      "args": ["-m", "simplebrain", "--mcp"],
      "env": { "BRAIN_ROOT": "/path/to/your/brain" }
    }
  }
}
```

| Tool | Description |
|---|---|
| `add_text_note` | Add a text note to the brain |
| `add_voice_note` | Add a voice note (base64-encoded audio) |
| `job_status` | Check processing status of an ingestion job |
| `search` | Search by query or tags |
| `get_chunk` | Get a specific knowledge chunk by ID |
| `list_topics` | List all topics with chunk counts |
| `list_tags` | List all tags with usage counts |
| `list_pending_folder_proposals` | List pending folder proposals |
| `confirm_folder_proposal` | Confirm a new folder |
| `reject_folder_proposal` | Reject a folder proposal |
| `list_conflicts` | List pending knowledge conflicts |
| `resolve_conflict` | Resolve a conflict |
| `revert_resolution` | Revert a resolution back to original state |
| `run_healer` | Trigger a manual healing scan |
| `get_brain_status` | Get queue depth, conflicts, and proposals summary |

---

## Directory Structure

```
<brain-root>/                   # set via --dir or BRAIN_ROOT in .env
├── _raw/
│   ├── audio/                  # Original audio recordings
│   └── transcripts/            # Raw transcripts and text notes
├── _queue/                     # Pending pipeline jobs
│   └── failed/                 # Failed jobs (for inspection)
├── _index/
│   ├── tags.json               # Tag -> [chunk_id] index
│   └── topics.json             # Topic -> [chunk_id] index
├── _conflicts/
│   ├── pending/                # Unresolved conflicts
│   └── resolution-log.json     # Resolved conflict history
├── _meta/
│   ├── setup.json              # Brain config and folder metadata
│   └── structure.json          # Folder list + pending proposals
└── knowledge/
    ├── _unfiled/               # Chunks awaiting folder assignment
    ├── projects/               # Your LLM-designed folders...
    │   └── README.md           # Auto-generated folder description
    └── research/
        └── README.md
```

### Chunk File Format

Each knowledge chunk is a Markdown file named `{title-slug}-{id}.md`:

```
knowledge/decisions/postgresql-chosen-for-main-datastore-a1b2c3d4.md
```

```markdown
---
id: a1b2c3d4
title: PostgreSQL chosen for main datastore
created: 2026-06-11T12:00:00+00:00
source_raw: _raw/transcripts/20260611T120000-a1b2c3d4.txt
tags: [#postgresql, #database, #decision]
links: [b5c6d7e8]
parent: null
user: alice
device: mac
---
We decided to use PostgreSQL for the main datastore. Key reasons: ACID compliance,
JSONB support, and the team's existing familiarity with it.
```

The `id` in the frontmatter is the stable reference used by the index and cross-links.
The filename slug is for human browsing only.

---

## Architecture

```
Voice/Text Input
      |
      v
 IngestService --> FileQueue --> BackgroundWorker
                                      |
                   +------------------+------------------+
                   v                  v                  v
            TranscribeStage     ChunkStage          TagStage
            (faster-whisper)    (LiteLLM)     (LiteLLM: title + tags)
                   |                  |                  |
                   +------------------+------------------+
                                      v
                                 FileStage --> SelfGrower (proposals)
                                      |
                                      v
                                 IndexStore
                                 (tags.json / topics.json)

 KnowledgeStore  -- Markdown files with YAML frontmatter
 SelfHealer      -- conflict detection, resolution, revert
 MCP Server      -- 15 tools via stdio
 FastAPI         -- REST API + mobile web UI
```

---

## Development

```bash
# Run tests
pytest tests/ -v

# End-to-end test (setup + server + ingest + worker + verify)
python e2e_test.py

# Run against a local LM Studio instance (no API key needed)
# In .env: LLM_PROVIDER=lmstudio, LLM_MODEL=google/gemma-4-e2b, LLM_API_BASE=http://localhost:1234/v1
simplebrain --setup --dir ./test-brain
```

---

## License

MIT
