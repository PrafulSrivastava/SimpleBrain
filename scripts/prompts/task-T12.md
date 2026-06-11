# SimpleBrain — Agent Task: T12 — FastAPI Web UI & REST API

You are a Pi coding agent implementing **Task 12** of the SimpleBrain project.
You are running IN PARALLEL with agent T11. Your files do NOT overlap.

## Your Mission
Implement **Task 12: FastAPI Web UI & REST API** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — check T4, T7, T8, T10 exports for service interfaces

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T4','T7','T8','T10'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T12.status = 'running';
c.tasks.T12.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T12 running');
"
```

## Your Task
Implement every step under `## Task 12: FastAPI Web UI & REST API` in the plan.

Files you own (ONLY touch these):
- `simplebrain/api/__init__.py`
- `simplebrain/api/routes.py`
- `simplebrain/api/ui.py`
- `ui/index.html`
- `tests/test_api.py`

## Parallel Agent Awareness
You are running alongside:
- **T11** → working on `simplebrain/mcp/server.py`

No file overlap. If T11 defines something you need, check `_agent_comms.json` messages.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T12.status = 'complete';
c.tasks.T12.completed = new Date().toISOString();
c.tasks.T12.exports = {
  factory: 'create_app(config: BrainConfig) -> FastAPI',
  path: 'simplebrain/api/routes.py',
  ui: 'ui/index.html',
  endpoints: ['GET /health','GET /status','POST /notes/text','POST /notes/voice','GET /topics','GET /tags','GET /search','GET /chunks/{id}','GET /proposals','POST /proposals/{id}/confirm','POST /proposals/{id}/reject','GET /conflicts','POST /conflicts/{id}/resolve','POST /conflicts/{id}/revert','POST /heal','GET /']
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T12 complete');
"
```

## Git Commit
```bash
git add simplebrain/api/ ui/ tests/test_api.py
git commit -m "feat: FastAPI REST API and mobile web UI"
```

**Begin now.**
