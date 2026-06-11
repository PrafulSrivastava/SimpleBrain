# SimpleBrain — Agent Task: T11 — MCP Server

You are a Pi coding agent implementing **Task 11** of the SimpleBrain project.
You are running IN PARALLEL with agent T12. Your files do NOT overlap.

## Your Mission
Implement **Task 11: MCP Server** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — check ALL prior task exports for the full interface picture

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T4','T7','T8','T9','T10'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T11.status = 'running';
c.tasks.T11.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T11 running');
"
```

## Your Task
Implement every step under `## Task 11: MCP Server` in the plan.

Files you own (ONLY touch these):
- `simplebrain/mcp/__init__.py`
- `simplebrain/mcp/server.py`
- `tests/test_mcp.py`

## Parallel Agent Awareness
You are running alongside:
- **T12** → working on `simplebrain/api/routes.py`, `simplebrain/api/ui.py`, `ui/index.html`

No file overlap. You own `mcp/`, T12 owns `api/` and `ui/`.

If T12 needs to know about a tool signature, leave a message in `_agent_comms.json`.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T11.status = 'complete';
c.tasks.T11.completed = new Date().toISOString();
c.tasks.T11.exports = {
  factory: 'create_mcp_server(config: BrainConfig) -> Server',
  path: 'simplebrain/mcp/server.py',
  tools: ['add_text_note','add_voice_note','job_status','search','get_chunk','list_topics','list_tags','list_pending_folder_proposals','confirm_folder_proposal','reject_folder_proposal','list_conflicts','resolve_conflict','revert_resolution','run_healer','get_brain_status']
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T11 complete');
"
```

## Git Commit
```bash
git add simplebrain/mcp/ tests/test_mcp.py
git commit -m "feat: MCP server with all tools"
```

**Begin now.**
