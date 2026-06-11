# Parallel Agent Development Workflow
**Version:** 1.0
**Date:** 2026-06-11
**Project:** SimpleBrain (reference implementation)
**Status:** Documented — pending conversion to skill

---

## Overview

This document captures a complete end-to-end workflow for taking an idea from raw concept
to parallel AI-agent implementation with built-in review and cost tracking.

The workflow was developed organically during the SimpleBrain project and is designed to
be extracted into a reusable skill + script bundle for any future project.

```
Idea
  |
  v
[Phase 1] Brainstorm + Design         -> spec doc
  |
  v
[Phase 2] Implementation Plan         -> plan doc with tasks + code
  |
  v
[Phase 3] Parallelism Analysis        -> wave map
  |
  v
[Phase 4] Script Generation           -> launcher + prompts + comms
  |
  v
[Phase 5] Parallel Execution          -> agents run, code written
  |
  v
[Phase 6] Review                      -> review report
  |
  v
[Phase 7] Cost + Token Report         -> cost breakdown
```

---

## Phase 1 — Brainstorm & Design

### Purpose
Turn a raw idea into a fully approved, written design spec before any code is written.

### Tool
`obra/superpowers@brainstorming` skill (install: `npx skills add obra/superpowers@brainstorming -g -y`)

### Process
1. Pi loads the brainstorming skill
2. Pi explores project context (existing files, git history)
3. Pi asks clarifying questions **one at a time** — purpose, constraints, tech stack, behaviour
4. Pi proposes 2-3 architecture approaches with trade-offs
5. Pi presents design section by section, user approves each
6. Pi writes spec to `docs/superpowers/specs/YYYY-MM-DD-<project>-design.md`
7. Pi runs spec self-review (no placeholders, no contradictions)
8. User reviews written spec
9. Pi transitions to Phase 2

### Outputs
- `docs/superpowers/specs/YYYY-MM-DD-<project>-design.md`
- Git commit: `docs: add <project> design spec`

### Key Decisions Captured in Spec
- Architecture approach chosen + reasoning
- Tech stack with justification
- Folder/data structure
- API/interface contracts
- Self-growing and self-healing behaviours
- Non-goals (explicit scope boundaries)

---

## Phase 2 — Implementation Plan

### Purpose
Break the approved spec into concrete, testable, step-by-step tasks with exact file paths,
full code, and exact test commands. No placeholders.

### Tool
`obra/superpowers@writing-plans` skill (install: `npx skills add obra/superpowers@writing-plans -g -y`)

### Process
1. Pi reads the approved spec
2. Pi maps out the full file structure — every file, its responsibility, its interfaces
3. Pi writes tasks following TDD: write failing test -> run it -> implement -> run again -> commit
4. Each step includes exact code, exact commands, expected output
5. Pi runs self-review: spec coverage check, placeholder scan, type consistency
6. Pi saves plan to `docs/superpowers/plans/YYYY-MM-DD-<project>-implementation.md`
7. User reviews plan

### Outputs
- `docs/superpowers/plans/YYYY-MM-DD-<project>-implementation.md`
- Git commit: `docs: add <project> implementation plan`

### Plan Structure
```
# <Project> Implementation Plan
> For agentic workers: REQUIRED SUB-SKILL: ...
Goal / Architecture / Tech Stack
---
## File Structure
## Task 1: <Name>
  Files: Create/Modify/Test
  - [ ] Step 1: Write failing test (with code)
  - [ ] Step 2: Run test (with expected output)
  - [ ] Step 3: Implement (with code)
  - [ ] Step 4: Run test again
  - [ ] Step 5: Commit (with exact git command)
## Task 2: ...
```

---

## Phase 3 — Parallelism Analysis

### Purpose
Identify which tasks can run simultaneously by mapping dependencies between them.
Collapse tasks into waves where all tasks within a wave are independent.

### Process (manual or Pi-assisted)
1. For each task, list its direct dependencies (what it imports / what must exist first)
2. Build a dependency graph
3. Group tasks into waves: Wave N contains all tasks whose dependencies are all in Wave < N
4. Verify: within a wave, no two tasks touch the same file

### Output: Wave Map
```
Wave 1: [T1]                    — foundation (models, scaffold)
Wave 2: [T2]                    — config (depends on T1)
Wave 3: [T3, T5, T6, T7]        — parallel: queue + pipeline stages + stores
Wave 4: [T4, T8, T10]           — parallel: ingest + file stage + healer
Wave 5: [T9, T13]               — parallel: worker + setup wizard
Wave 6: [T11, T12]              — parallel: mcp + api
Wave 7: [T14]                   — final: entry point + readme
```

### Rules for Valid Parallelism
- Tasks in the same wave MUST NOT share any files
- Tasks in the same wave MUST NOT depend on each other
- Each task's exports (interfaces) must be stable before dependent waves start
- Git commits per task must specify only that task's files (avoid `git add .`)

---

## Phase 4 — Script Generation

### Purpose
Generate the launcher script, per-task prompt files, and central comms file
that enable parallel agent execution via Windows Terminal.

### Scripts Generated

#### `_agent_comms.json` (project root)
Central coordination file. All agents read and write to this.

```json
{
  "version": "1.0",
  "project": "<name>",
  "plan": "docs/superpowers/plans/<plan-file>.md",
  "waves": { "1": ["T1"], "2": ["T2", "T3"], ... },
  "tasks": {
    "T1": {
      "name": "<task name>",
      "wave": 1,
      "status": "pending | running | complete | failed",
      "started": null,
      "completed": null,
      "notes": "",
      "exports": {}
    }
  },
  "messages": [],
  "shared_context": {}
}
```

#### `scripts/launch-wave.ps1`
Main launcher. Usage:
```powershell
.\scripts\launch-wave.ps1 -Check          # show all task statuses
.\scripts\launch-wave.ps1 -Wave <1-7>     # launch wave N in Windows Terminal
```

Behaviour:
- Validates wave number
- Checks prior wave is complete (reads `_agent_comms.json`) — blocks if not
- Generates `.run/task-TN.ps1` launcher scripts (no BOM, UTF-8)
- Launches `wt` with one tab per task in the wave
- Each tab: `powershell -NoExit -File scripts/.run/task-TN.ps1`
- Each run script: `Set-Location <project> && pi '@scripts/prompts/task-TN.md'`

#### `scripts/prompts/task-TN.md` (one per task)
Task-specific prompt loaded into Pi. Structure:
```markdown
# <Project> - Agent Task: TN - <Name>

You are a Pi coding agent implementing Task N...

## Files You Need to Read First
1. Read the full plan: docs/superpowers/plans/<plan>.md
2. Read _agent_comms.json

## Before You Start
[node one-liner to mark task as running in _agent_comms.json]

## Your Task
Implement every step under ## Task N in the plan.

## Files You Own (ONLY touch these)
- <file1>
- <file2>

## Parallel Agent Awareness
You are running alongside: TM -> working on <files>
[no overlap note]

## Inter-Agent Messaging (if needed)
[node one-liner to post message to _agent_comms.json]

## After Completion
[node one-liner to mark complete + write exports to _agent_comms.json]

## Git Commit
git add <only-your-files>
git commit -m "feat: <task description>"

Begin now.
```

#### `scripts/review.ps1`
Review launcher with model switching. Usage:
```powershell
.\scripts\review.ps1
```

Behaviour:
1. Reads current model from `~/.pi/agent/settings.json`
2. Switches to review model (e.g. `claude-opus-4.6`)
3. Launches Pi interactively in current terminal with `@scripts/prompts/review.md`
4. On exit (including Ctrl+C / crash): restores original model via `try/finally`
5. Reports review file location

#### `scripts/prompts/review.md`
Review prompt loaded into Pi for the review session. Steps:
1. Read the implementation plan
2. Read `_agent_comms.json` — check task statuses and exports
3. Verify all files from plan exist
4. Run full test suite (`pytest tests/ -v --tb=short`)
5. Spot-check key implementations against plan
6. Check chunk/data format matches spec
7. Check `_agent_comms.json` exports match what downstream tasks consumed
8. Write structured review report to `docs/superpowers/reviews/YYYY-MM-DD-<project>-review.md`
9. Commit the review

---

## Phase 5 — Parallel Execution

### Process
```powershell
# Run waves in order, launching each only when prior wave is done
.\scripts\launch-wave.ps1 -Wave 1

# Monitor status
.\scripts\launch-wave.ps1 -Check

# When Wave 1 shows [DONE], launch Wave 2
.\scripts\launch-wave.ps1 -Wave 2

# ... continue through all waves
```

### Agent Behaviour (enforced by prompts)
Each agent:
1. Reads the full plan
2. Checks `_agent_comms.json` for prior wave exports and messages
3. Marks its task `running` in comms
4. Implements every step from the plan exactly
5. Runs its tests
6. Marks its task `complete` in comms with exports
7. Commits only its own files

### Inter-Agent Communication
Agents communicate via `_agent_comms.json`:
- `tasks.TN.status` — running / complete / failed
- `tasks.TN.exports` — interfaces, method signatures, file paths exported to downstream
- `messages[]` — direct messages between agents (from/to/text/timestamp)
- `shared_context{}` — global key-value store for cross-wave facts

### Race Condition Mitigation
- Agents in the same wave write only to their own `tasks.TN` key
- Writes are fast (node one-liners)
- Risk is low but: launch agents 30s apart within a wave if cautious
- Never use `git add .` — always commit specific files

---

## Phase 6 — Review

### Process
```powershell
.\scripts\review.ps1
```

### Model Strategy
- Use a more capable / slower model for review (e.g. `claude-opus-4.6`)
- Use faster/cheaper model for implementation agents (e.g. `claude-sonnet-4.6`)
- `review.ps1` handles the switch automatically via `~/.pi/agent/settings.json`

### Review Report Structure
```markdown
# <Project> Implementation Review
Date / Reviewer / Model

## Summary
## Test Results (total / passed / failed / errors)
## Task Completion (table)
## File Coverage (missing files)
## Issues Found (Critical / Warning / Minor)
## Spec Deviations
## Recommendations
## Verdict (APPROVED / APPROVED WITH FIXES / NEEDS WORK)
```

### Output
- `docs/superpowers/reviews/YYYY-MM-DD-<project>-review.md`
- Git commit: `review: <project> implementation review by <model>`

---

## Phase 7 — Cost & Token Report

### Process
Run the session inspector script to aggregate token usage and cost across all project sessions.

```powershell
python scripts/session-cost.py
```

### Pi Session File Structure
Pi stores sessions as `.jsonl` files in:
`~/.pi/agent/sessions/<encoded-cwd>/<timestamp>_<uuid>.jsonl`

Relevant entry types:
- `session` — session start, contains `id`, `timestamp`, `cwd`
- `model_change` — contains `provider`, `modelId`
- `message` — assistant messages contain `usage` with `input`, `output`, `cacheRead`, `cacheWrite`, `cost.total`

### Metrics Reported
| Metric | Description |
|---|---|
| Input tokens | Tokens in each request prompt |
| Output tokens | Tokens generated by the model |
| Cache read tokens | Tokens served from prompt cache (cheap) |
| Cache write tokens | Tokens written to prompt cache |
| Cost per session | USD based on model pricing |
| Grand total cost | Sum across all project sessions |

### Cost Insight from SimpleBrain
- Total: **$10.33** for full brainstorm + plan + 14 parallel agents + review
- Main brainstorm session: **$5.82** (56%) — large plan file read many times
- 14 parallel agent sessions: **$3.73** (~$0.27/task) — cache very effective
- Review session (opus): **$0.73** — more expensive but thorough
- Cache hit rate was very high — 14.7M cache reads vs 798K writes

---

## File Inventory

```
<project-root>/
|
|- _agent_comms.json                          # central comms (all agents read/write)
|
|- scripts/
|  |- launch-wave.ps1                         # wave launcher
|  |- review.ps1                              # review launcher with model switch
|  |- session-cost.py                         # cost + token report       [TODO: extract]
|  |- .run/                                   # auto-generated run scripts (gitignored)
|  |- prompts/
|     |- task-T1.md ... task-TN.md            # per-task agent prompts
|     |- review.md                            # review agent prompt
|
|- docs/
   |- superpowers/
      |- specs/
      |  |- YYYY-MM-DD-<project>-design.md    # approved design spec
      |- plans/
      |  |- YYYY-MM-DD-<project>-implementation.md  # implementation plan
      |- reviews/
         |- YYYY-MM-DD-<project>-review.md    # post-implementation review
```

---

## Windows-Specific Notes

### PowerShell Script Rules (learned the hard way)
- No Unicode characters in `.ps1` files — use plain ASCII only
  - Em dash `—` -> `-`
  - Right arrow `->` -> `->`
  - Box drawing `─` -> `-`
- No `$var:` patterns — PowerShell reads `:` after a variable as a drive letter
- No here-strings `@"..."@` when content has `$var:` patterns — use string concatenation
- `Set-Content -Encoding UTF8` writes a BOM — use `[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))` instead
- Always parse-check `.ps1` files: `[System.Management.Automation.Language.Parser]::ParseFile(...)`

### Windows Terminal (wt.exe)
- Multiple tabs: `wt new-tab --title "T1" <cmd> ; new-tab --title "T2" <cmd>`
- Each tab title maps to the task ID for easy monitoring
- `Start-Process "wt" -ArgumentList $wtArgs` — fire and forget (non-blocking)
- For blocking (review script): run Pi directly with `& pi "@prompt.md"` in current terminal

### Model Switching
- Pi settings: `~/.pi/agent/settings.json` — `defaultProvider` + `defaultModel`
- Read/write with `ConvertFrom-Json` / `ConvertTo-Json -Depth 10`
- Always use `try/finally` when switching models to guarantee restore

---

## Skill File Sketch

The following is a draft `SKILL.md` for packaging this entire workflow as a reusable Pi skill.
Full implementation of the skill is a separate project.

```markdown
---
name: parallel-agent-workflow
description: >
  Full workflow for taking an idea from concept to parallel AI-agent implementation.
  Covers brainstorm, design spec, implementation plan, parallelism analysis,
  script generation, parallel execution, review, and cost reporting.
  Use this when starting any new software project with Pi.
---

# Parallel Agent Development Workflow

## When to Use
- Starting a new project from scratch
- When a project is large enough to benefit from parallel agents (5+ tasks)
- When you want deterministic, reviewable, cost-tracked development

## Checklist

1. **Phase 1 - Brainstorm**
   - [ ] Run brainstorming skill: ask clarifying questions, propose approaches
   - [ ] Present design sections, get approval
   - [ ] Write spec to `docs/superpowers/specs/`
   - [ ] Commit spec

2. **Phase 2 - Plan**
   - [ ] Run writing-plans skill
   - [ ] Verify no placeholders, full code in every step
   - [ ] Write plan to `docs/superpowers/plans/`
   - [ ] Commit plan

3. **Phase 3 - Parallelism**
   - [ ] Map task dependencies
   - [ ] Group into waves (no intra-wave file conflicts)
   - [ ] Verify wave map

4. **Phase 4 - Generate Scripts**
   - [ ] Initialize `_agent_comms.json`
   - [ ] Generate `scripts/launch-wave.ps1`
   - [ ] Generate `scripts/prompts/task-TN.md` for each task
   - [ ] Generate `scripts/review.ps1` + `scripts/prompts/review.md`
   - [ ] Parse-check all `.ps1` files
   - [ ] ASCII-check all files
   - [ ] Commit scripts

5. **Phase 5 - Execute**
   - [ ] `.\scripts\launch-wave.ps1 -Wave 1`
   - [ ] Monitor: `.\scripts\launch-wave.ps1 -Check`
   - [ ] Launch each subsequent wave when prior is complete
   - [ ] Continue through all waves

6. **Phase 6 - Review**
   - [ ] `.\scripts\review.ps1`
   - [ ] Read review report
   - [ ] Address any Critical issues

7. **Phase 7 - Cost Report**
   - [ ] `python scripts/session-cost.py`
   - [ ] Record totals

## Script Templates
[links to template files in skill package]

## Customisation Points
- `REVIEW_MODEL` in `review.ps1` — model used for review
- `DEFAULT_MODEL` in `review.ps1` — model to restore after review
- Wave map in `launch-wave.ps1` — project-specific
- Task prompts in `scripts/prompts/` — project-specific
- Comms file structure in `_agent_comms.json` — schema is fixed, task list varies
```

---

## TODO — Scripts Still to Extract

| Script | Status | Description |
|---|---|---|
| `scripts/session-cost.py` | Not yet saved | Reads Pi session files, reports token usage and cost per session |
| `scripts/init-project.ps1` | Not yet written | Scaffolds `_agent_comms.json` + `scripts/` from a plan file automatically |
| `scripts/wave-status.ps1` | Covered by `-Check` flag | Standalone status checker |
| `scripts/session-cost.ps1` | Not yet written | PowerShell port of session-cost.py for Windows-only environments |
