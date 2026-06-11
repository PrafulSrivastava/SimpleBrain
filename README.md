# 🧠 SimpleBrain

A self-organising, self-growing, and self-healing second brain.

Drop voice or text notes — SimpleBrain transcribes, chunks, tags, and files them automatically using an LLM pipeline. Knowledge is stored as human-readable Markdown files with YAML frontmatter. The brain exposes a full REST API, a mobile web UI, and an MCP server for AI tool integration.

---

## Features

- **Voice + Text Ingest** — instant queueing, async pipeline processing
- **5-Stage Pipeline** — Transcribe → Chunk → Tag → File → Index
- **Self-Organising** — LLM proposes and creates new folders as knowledge grows
- **Self-Healing** — detects factual conflicts, structural issues, and topic pivots
- **MCP Server** — 15 tools for Claude Desktop / MCP CLI integration
- **Mobile Web UI** — tap-to-record + text input, optimised for iPhone Safari
- **Human-Readable Storage** — all knowledge as `.md` files, fully portable

---

## Quickstart

```bash
# Install
pip install -e .
cp .env.example .env   # add your LLM API key

# First-time setup (generates your folder structure)
python -m simplebrain --setup

# Run the brain (API server + background worker)
python -m simplebrain

# Run as MCP server for Claude Desktop / MCP CLI
python -m simplebrain --mcp
```

---

## CLI Flags

| Flag | Description |
|---|---|
| *(none)* | Start API server + background pipeline worker |
| `--setup` | Run interactive setup wizard |
| `--mcp` | Start as MCP stdio server |
| `--host HOST` | API bind host (default: `0.0.0.0`) |
| `--port PORT` | API port (default: `8000`) |

---

## iPhone / Mobile Access

1. Run `python -m simplebrain` on your Mac
2. Open `http://<your-mac-ip>:8000` in Safari on your iPhone
3. **Add to Home Screen** for instant native-app-like access
4. Tap the microphone to record a voice note, or type in the text box

---

## REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/status` | Brain status (queue depth, conflicts, proposals) |
| `POST` | `/notes/text` | Add a text note |
| `POST` | `/notes/voice` | Add a voice note (base64 audio) |
| `GET` | `/topics` | List topics with chunk counts |
| `GET` | `/tags` | List tags with usage counts |
| `GET` | `/search?query=...` | Search knowledge base |
| `GET` | `/chunks/{id}` | Get a specific chunk |
| `GET` | `/proposals` | List pending folder proposals |
| `POST` | `/proposals/{id}/confirm` | Confirm a folder proposal |
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
~/simplebrain/                  # BRAIN_ROOT
├── _raw/
│   ├── audio/                  # Original audio recordings
│   └── transcripts/            # Raw transcripts and text notes
├── _queue/                     # Pending pipeline jobs
│   └── failed/                 # Failed jobs (for inspection)
├── _index/
│   ├── tags.json               # Tag → [chunk_id] index
│   └── topics.json             # Topic → [chunk_id] index
├── _conflicts/
│   ├── pending/                # Unresolved conflicts
│   └── resolution-log.json     # Resolved conflict history
├── _meta/
│   ├── setup.json              # Brain configuration
│   └── structure.json          # Folder structure + proposals
└── knowledge/
    ├── _unfiled/               # Chunks awaiting folder assignment
    ├── projects/               # Your custom folders...
    └── research/
```

Each knowledge chunk is stored as a Markdown file with YAML frontmatter:

```markdown
---
id: a1b2c3d4
created: 2026-06-11T12:00:00
source_raw: _raw/transcripts/20260611T120000-a1b2c3d4.txt
tags: [#mcp, #ai, #protocol]
links: [b5c6d7e8]
user: alice
device: mac
---
MCP is a protocol for connecting AI models to external tools and data sources.
```

---

## Environment Variables

See `.env.example` for all options:

```bash
BRAIN_ROOT=~/simplebrain       # Where to store the brain
BRAIN_USER=default             # Default username
BRAIN_DEVICE=unknown           # Default device name
LLM_PROVIDER=openai            # openai | anthropic | ollama
LLM_MODEL=gpt-4o-mini          # Any LiteLLM-supported model
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# OLLAMA_BASE_URL=http://localhost:11434
HEALER_SCHEDULE=daily          # daily | weekly | manual
```

---

## Development

```bash
# Run tests
pytest tests/ -v

# Run with local Ollama (no API key needed)
LLM_PROVIDER=ollama LLM_MODEL=ollama/llama3.2 python -m simplebrain
```

---

## Architecture

```
Voice/Text Input
      │
      ▼
 IngestService ──► FileQueue ──► BackgroundWorker
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                   ▼
             TranscribeStage     ChunkStage          TagStage
             (faster-whisper)    (LiteLLM)           (LiteLLM)
                    │                  │                   │
                    └──────────────────┼───────────────────┘
                                       ▼
                                  FileStage ──► SelfGrower (proposals)
                                       │
                                       ▼
                                  IndexStore
                                  (tags.json / topics.json)

 KnowledgeStore (Markdown files)
 SelfHealer (conflict detection + resolution)
 MCP Server (15 tools via stdio)
 FastAPI (REST + mobile UI)
```

---

## License

MIT
