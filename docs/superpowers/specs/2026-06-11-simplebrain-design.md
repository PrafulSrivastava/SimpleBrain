# SimpleBrain — Design Spec
**Date:** 2026-06-11  
**Status:** Approved  
**Author:** srivpra

---

## Overview

SimpleBrain is a self-organising, self-growing, and self-healing second brain. Users drop voice or text notes; the system transcribes, chunks, tags, and files them automatically into a human-readable folder structure. It is exposed as an MCP server for AI tool and CLI consumption, with a lightweight web UI for iPhone input over local WiFi.

---

## Goals

- Accept voice and text notes with zero friction (drop and forget)
- Organise notes into a meaningful folder structure driven by LLM, not manual effort
- Keep raw data untouched and separate for future migrations
- Auto-tag and auto-link chunks by shared topics
- Grow its own structure with user confirmation
- Detect and resolve conflicts with a full audit trail and revert capability
- Run fully locally on Mac (Apple Silicon), accessible from iPhone over WiFi
- Expose all capabilities via MCP for CLI and AI tool consumption

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   INPUT LAYER                        │
│   Voice (mic/file)          Text (web UI / MCP)     │
└────────────────┬────────────────────────┬───────────┘
                 │                        │
                 ▼                        ▼
┌─────────────────────────────────────────────────────┐
│                 INGEST SERVICE  (FastAPI)             │
│  • Saves raw audio/text to _raw/                     │
│  • Drops job into _queue/  (instant return)          │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              BACKGROUND WORKER  (watchdog)           │
│  Picks up jobs from _queue/ and runs pipeline:       │
│                                                      │
│  [Transcribe] → [Chunk] → [Tag] → [File] → [Index]  │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                 KNOWLEDGE STORE                      │
│  _raw/          → original audio + transcripts      │
│  _queue/        → pending jobs                      │
│  _index/        → tag index, topic map              │
│  _conflicts/    → resolution log + revert history   │
│  knowledge/     → filed semantic chunks (markdown)  │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                   MCP SERVER                         │
│  Exposes brain as tools: add_note, search, query,   │
│  list_topics, resolve_conflict, revert              │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| STT (Voice-to-Text) | `faster-whisper` (fully local, Apple Silicon optimised) |
| LLM (chunking, tagging, filing) | Configurable: OpenAI / Anthropic / Ollama (local) |
| MCP Server | MCP Python SDK |
| Web UI + REST API | FastAPI |
| File watching (worker) | `watchdog` |
| Storage format | Markdown files with YAML frontmatter |
| Queue | File-based (`_queue/` folder) |

---

## Folder Structure

```
~/simplebrain/
│
├── _raw/                          # Source of truth, never modified
│   ├── audio/                     # Original voice recordings (.m4a, .wav)
│   └── transcripts/               # Raw unprocessed transcriptions (.txt)
│
├── _queue/                        # Async job queue (file-based)
│   ├── <timestamp>-<id>.json      # One job file per ingestion
│   └── failed/                    # Failed jobs with error logs
│
├── _index/                        # Fast lookup layer
│   ├── tags.json                  # tag → [list of chunk file paths]
│   └── topics.json                # topic → [list of chunk file paths]
│
├── _conflicts/                    # Self-healing layer
│   ├── pending/                   # Flagged conflicts awaiting resolution
│   └── resolution-log.json        # Full audit trail + revert snapshots
│
├── _meta/                         # Brain configuration
│   ├── setup.json                 # Setup interview answers, brain purpose
│   └── structure.json             # Current folder taxonomy + pending proposals
│
└── knowledge/                     # The actual brain (LLM-organised)
    ├── _unfiled/                  # Chunks held pending folder confirmation
    ├── <topic-a>/
    │   ├── <chunk-001>.md
    │   └── <chunk-002>.md
    ├── <topic-b>/
    │   └── <chunk-003>.md
    └── ...
```

---

## Chunk Format

Each chunk is a markdown file with YAML frontmatter:

```markdown
---
id: abc123
created: 2026-06-11T10:30:00
source_raw: _raw/transcripts/2026-06-11-abc123.txt
tags: [#mcp, #architecture, #simplebrain]
links: [xyz456, def789]     # chunk IDs sharing tags
parent: null                # UUID of parent chunk if split from a large note
user: srivpra               # who added this note
device: macbook             # mac | iphone | cli
---

Chunk content here...
```

---

## Processing Pipeline

Each job in `_queue/` runs through 5 sequential stages:

### Stage 1 — Transcribe *(voice only)*
- `faster-whisper` runs locally on the raw audio file
- Output saved to `_raw/transcripts/<timestamp>-<id>.txt`
- Skipped for text notes

### Stage 2 — Chunk
- LLM splits the full text into semantic chunks — one focused idea per chunk
- Large notes → multiple chunk files with `parent` reference
- Small notes → single chunk file
- Each chunk assigned a UUID

### Stage 3 — Tag
- LLM reads each chunk and extracts free-form tags automatically
- Tags written into chunk frontmatter
- No fixed taxonomy — fully automatic

### Stage 4 — File
- LLM reads each chunk + tags and selects the best matching folder
- **Fits existing folder** → filed directly
- **No folder fits** → proposal created in `_meta/structure.json`, chunk held in `knowledge/_unfiled/`, user notified
- User confirms or rejects folder proposal before it is created

### Stage 5 — Index
- `_index/tags.json` and `_index/topics.json` updated
- Cross-links computed: chunks sharing ≥1 tag added to each other's `links:` frontmatter

### Error Handling
- Failed jobs moved to `_queue/failed/` with error log
- Retryable on next worker cycle
- Raw data in `_raw/` always intact — no data loss

---

## Self-Growing

Triggered during Stage 4 when no existing folder fits a chunk:

```
LLM detects no good folder match
        ↓
Proposes new folder name + reasoning
        ↓
Notification sent to user (web UI / CLI)
        ↓
User confirms or rejects
        ↓
Confirmed → folder created, chunk filed
Rejected  → user picks existing folder, chunk filed there
```

Proposals stored in `_meta/structure.json` as `pending` until resolved. The brain never extends its own structure without user approval.

---

## Self-Healing

A **Healer** process runs on a configurable schedule (daily / weekly / manual):

### Detection
Scans `knowledge/` for:
- **Factual conflicts** — same topic, contradicting statements across chunks
- **Structural issues** — duplicate chunks, orphaned files, tag mismatches
- **Pivots** — topic drift detected across a folder over time

### Resolution Flow
```
Issue detected → written to _conflicts/pending/<id>.json
        ↓
User notified with clear conflict summary
        ↓
User resolves: merge | keep_newer | keep_older | keep_both | archive
        ↓
Resolution executed + logged to _conflicts/resolution-log.json
```

### Resolution Log Entry
```json
{
  "id": "conflict-001",
  "detected": "2026-06-11T22:00:00",
  "type": "factual_conflict",
  "chunks_involved": ["abc123", "xyz456"],
  "summary": "Two notes contradict each other on MCP transport layer",
  "resolution": "kept_newer",
  "resolved_by": "srivpra",
  "resolved_at": "2026-06-11T22:05:00",
  "snapshot": {}
}
```

The `snapshot` field preserves full pre-resolution chunk content for revert.

### Revert
- Any resolution can be reverted via `revert_resolution("<conflict-id>")`
- Restores original chunk files from snapshot
- Removes resolution log entry

---

## MCP Server Tools

### Ingestion
| Tool | Description |
|---|---|
| `add_text_note(text, user)` | Drops text job to queue, returns job_id immediately |
| `add_voice_note(audio_file_path, user)` | Saves audio to _raw/, drops job to queue, returns job_id |
| `job_status(job_id)` | Returns current pipeline stage or complete/failed |

### Query
| Tool | Description |
|---|---|
| `search(query, tags=[], user=None)` | Searches _index/, returns matching chunks |
| `get_chunk(chunk_id)` | Returns full chunk content + frontmatter |
| `list_topics()` | Returns folder structure with chunk counts |
| `list_tags()` | Returns all tags with usage counts |

### Self-Growing
| Tool | Description |
|---|---|
| `list_pending_folder_proposals()` | Returns proposed new folders awaiting confirmation |
| `confirm_folder_proposal(proposal_id)` | Approves folder, files held chunks |
| `reject_folder_proposal(proposal_id, target_folder)` | Rejects proposal, files chunks into target_folder |

### Self-Healing
| Tool | Description |
|---|---|
| `list_conflicts()` | Returns all pending conflicts with summaries |
| `resolve_conflict(conflict_id, resolution)` | Resolves a flagged conflict |
| `revert_resolution(conflict_id)` | Restores pre-resolution state from snapshot |
| `run_healer()` | Manually triggers a healing scan |

### Setup & Status
| Tool | Description |
|---|---|
| `setup(answers)` | Runs setup interview, generates initial folder structure |
| `get_brain_status()` | Returns queue depth, pending conflicts, pending proposals, last healed |

---

## Setup Flow

Run once on first launch via CLI or web UI:

```
Q1: What is this knowledge base about?
Q2: Who will be using it? (usernames, comma-separated)
Q3: What are the main topics or areas you want to organise?
Q4: How often should the self-healer run? (Daily / Weekly / Manual)
Q5: Which LLM should power the brain? (OpenAI / Anthropic / Ollama)
Q6: Which model? (e.g. gpt-4o-mini / gpt-4o / claude-3-5-haiku)
```

After the interview:
1. LLM generates initial `knowledge/` folder structure from answers
2. User confirms structure before any folders are created
3. `faster-whisper` model downloaded (once)
4. LLM API key validated or Ollama connection checked
5. Background worker started
6. MCP server started
7. FastAPI web UI started — local URL displayed for iPhone Safari bookmark

---

## iPhone Access

- FastAPI serves a minimal mobile web UI on local WiFi (e.g. `http://192.168.x.x:8000`)
- Supports: voice recording (browser mic), text input, job status, pending proposals, pending conflicts
- No app store required — bookmarked in Safari as a home screen shortcut
- All REST endpoints map 1:1 to MCP tools

---

## Non-Goals (v1)

- No vector embeddings or semantic similarity search (vectorless by design)
- No multi-device sync (Mac is the single source of truth)
- No native iPhone app
- No end-to-end encryption (local trust model)
- No multi-brain support (single knowledge base per instance)
