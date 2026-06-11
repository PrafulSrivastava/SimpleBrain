# SimpleBrain — Agent Task: T10 — Self-Healer

You are a Pi coding agent implementing **Task 10** of the SimpleBrain project.
You are running IN PARALLEL with agents T4 and T8. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 10: Self-Healer** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — check T7 exports for KnowledgeStore interface, T1 exports for Conflict models

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T2','T7'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T10.status = 'running';
c.tasks.T10.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T10 running');
"
```

## Your Task
Implement every step under `## Task 10: Self-Healer` in the plan.

Files you own (ONLY touch these):
- `simplebrain/brain/healer.py`
- `tests/test_healer.py`

Note: `simplebrain/brain/__init__.py` is shared with T8. Create it as an empty file only if T8 hasn't created it yet. If it exists, leave it alone.

## Parallel Agent Awareness
You are running alongside:
- **T4** → working on `simplebrain/store/raw.py` and `ingest/service.py`
- **T8** → working on `simplebrain/pipeline/file.py` and `simplebrain/brain/grower.py`

T8 owns `brain/grower.py`, you own `brain/healer.py` — no conflict.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T10.status = 'complete';
c.tasks.T10.completed = new Date().toISOString();
c.tasks.T10.exports = {
  class: 'SelfHealer',
  path: 'simplebrain/brain/healer.py',
  methods: ['scan() -> list[Conflict]', 'resolve(conflict_id, resolution, resolved_by)', 'revert(conflict_id, knowledge_store)', 'list_pending() -> list[Conflict]', 'load_resolution_log() -> list[dict]']
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T10 complete');
"
```

## Git Commit
```bash
git add simplebrain/brain/healer.py tests/test_healer.py
git commit -m "feat: self-healer with conflict detection, resolution, and revert"
```

**Begin now.**
