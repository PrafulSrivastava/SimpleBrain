# Folder Structure UI — Design Spec

## Summary

A browser-based UI at `/ui/setup.html` that lets users configure the SimpleBrain knowledge-base folder structure. It combines an AI-assisted wizard (describe → generate → edit → apply) with a lightweight post-setup folder manager (add/rename/delete).

## User Flows

### Flow 1: Initial Setup (Wizard)

1. User navigates to `/ui/setup.html` (linked from main UI gear icon)
2. If no structure exists, the wizard view is shown by default
3. User types a free-form description of their knowledge base
4. Clicks "Generate Structure" → `POST /structure/propose`
5. Backend calls `SetupWizard.propose(description)` and returns the proposal JSON
6. UI renders the proposal as a list of editable folder cards:
   - Each card shows: name (editable), description (editable), examples (editable comma-list)
   - Delete button per card (with immediate removal from list, no extra confirm)
   - "Add Folder" button at the bottom appends a blank card
   - "Regenerate" button re-submits the same description for a fresh proposal
7. User clicks "Apply" → `POST /structure/apply` with the (possibly edited) proposal
8. Backend calls `SetupWizard.apply()`, creates folders + metadata on disk
9. UI shows success message and transitions to the folder manager view

### Flow 2: Post-Setup Folder Manager

1. On page load, if a structure already exists (`GET /structure` returns folders), show the manager view
2. Displays current folders as a simple list (name + description)
3. Actions available:
   - **Add folder**: inline form at bottom (name + description fields + "Add" button)
   - **Rename**: click folder name → becomes editable input → blur/enter saves via `PATCH /structure/folders/{name}`
   - **Delete**: trash icon per folder → confirmation prompt → `DELETE /structure/folders/{name}`
4. A "Redesign with AI" button switches back to the wizard flow (pre-fills the existing summary as the description)

## API Endpoints (New)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| `GET` | `/structure` | — | `{summary, healer_schedule, folders: [{name, display, description, examples}]}` | Returns current structure from `_meta/structure.json`. Returns `{folders: []}` if none exists. |
| `POST` | `/structure/propose` | `{description: string}` | `{summary, healer_schedule, folders: [...]}` | Calls `SetupWizard.propose()`. May take 5-15s (LLM call). |
| `POST` | `/structure/apply` | `{summary, healer_schedule, folders: [...]}` | `{applied: true, folder_count: int}` | Calls `SetupWizard.apply()`. Creates dirs + metadata. |
| `POST` | `/structure/folders` | `{name, display?, description?, examples?}` | `{created: true, folder: {...}}` | Adds a single folder to existing structure. Creates dir + README. |
| `PATCH` | `/structure/folders/{name}` | `{new_name?, display?, description?, examples?}` | `{updated: true, folder: {...}}` | Updates a folder's metadata. If `new_name` is provided and differs from `{name}`, renames the directory on disk. |
| `DELETE` | `/structure/folders/{name}` | — | `{deleted: true}` | Removes folder from metadata. Does NOT delete files on disk (moves to `_unfiled`). |

## Frontend

### File: `ui/setup.html`

Single-page HTML file following the same design system as `ui/index.html`:
- Same CSS variables, dark/light mode toggle, color schemes
- Same card-based layout, same font stack
- No build step, no framework — vanilla HTML/CSS/JS

### Layout

```
┌─────────────────────────────────────┐
│  Header: SimpleBrain logo + gear    │
│  (same brand bar as index.html)     │
├─────────────────────────────────────┤
│                                     │
│  [Wizard View]  OR  [Manager View]  │
│                                     │
├─────────────────────────────────────┤
│  Wizard View:                       │
│  ┌───────────────────────────────┐  │
│  │ textarea: "Describe your      │  │
│  │ knowledge base..."            │  │
│  └───────────────────────────────┘  │
│  [Generate Structure]               │
│                                     │
│  ── Proposal (when returned) ──     │
│  ┌─ Folder Card ─────────────────┐  │
│  │ name: [research-notes    ] ✕  │  │
│  │ desc: [Papers, findings...]   │  │
│  │ examples: [paper1, paper2]    │  │
│  └───────────────────────────────┘  │
│  ┌─ Folder Card ─────────────────┐  │
│  │ ...                           │  │
│  └───────────────────────────────┘  │
│  [+ Add Folder]                     │
│  [Regenerate]  [Apply Structure]    │
│                                     │
├─────────────────────────────────────┤
│  Manager View:                      │
│  ┌───────────────────────────────┐  │
│  │ research-notes  — Papers...  🗑│  │
│  │ daily-log       — Daily...   🗑│  │
│  │ projects        — Active...  🗑│  │
│  └───────────────────────────────┘  │
│  [name] [description] [+ Add]       │
│  [Redesign with AI]                 │
└─────────────────────────────────────┘
```

### States

- **Empty state**: No structure exists → wizard view with description textarea
- **Loading**: Spinner/disabled button while waiting for LLM proposal
- **Proposal state**: Editable cards rendered from AI response
- **Manager state**: Existing folders listed with edit/delete capabilities
- **Error state**: Inline error messages (e.g., LLM timeout, duplicate folder name)

## Backend Implementation

All new endpoints go in `simplebrain/api/routes.py` within the existing `create_app()` function.

The `SetupWizard` and `SelfGrower` classes already provide the core logic:
- `SetupWizard.propose(description)` → generates the AI proposal
- `SetupWizard.apply(proposal)` → writes folders + metadata to disk
- `SelfGrower.get_folder_details()` → reads current structure
- `SelfGrower.load_structure()` / `save_structure()` → direct metadata access

New logic needed:
- Add/rename/delete individual folders (currently only bulk-apply exists)
- When deleting a folder, move its contents to `knowledge/_unfiled/` rather than deleting

## Link from Main UI

Add a gear icon button in the `index.html` header (next to the mode toggle) that links to `/ui/setup.html`. Simple anchor tag, no JavaScript needed.

## Constraints

- No external dependencies (no React, no Tailwind, no npm)
- Must work on mobile (same responsive approach as index.html)
- Proposal generation may take 5-15 seconds — needs clear loading state
- Folder names must be validated: lowercase, hyphen-separated, no spaces, no special chars
- "archive" folder cannot be deleted (enforced backend-side)

## Testing

- Unit tests for new API endpoints (same pattern as existing `tests/test_api.py`)
- Test that `DELETE /structure/folders/{name}` moves files to `_unfiled`
- Test that `POST /structure/propose` returns valid structure
- Test validation: duplicate names, invalid characters, deleting "archive"
