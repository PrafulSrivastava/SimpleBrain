# SimpleBrain — Agent Task: T3 — File Queue

You are a Pi coding agent implementing **Task 3** of the SimpleBrain project.
You are running IN PARALLEL with agents T5, T6, and T7. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 3: File Queue** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read the comms file: `_agent_comms.json` — check T2 exports for BrainConfig interface

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
if (c.tasks.T2.status !== 'complete') { console.error('T2 not complete! Cannot proceed.'); process.exit(1); }
c.tasks.T3.status = 'running';
c.tasks.T3.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T3 running');
"
```

## Your Task
Implement every step under `## Task 3: File Queue` in the plan.

Files you own (ONLY touch these):
- `simplebrain/ingest/__init__.py`
- `simplebrain/ingest/queue.py`
- `tests/test_queue.py`

## Parallel Agent Awareness
You are running alongside:
- **T5** → working on `simplebrain/pipeline/transcribe.py`
- **T6** → working on `simplebrain/pipeline/chunk.py` and `tag.py`
- **T7** → working on `simplebrain/store/knowledge.py` and `index.py`

These files DO NOT overlap. Do not touch their files. Do not wait for them.
If you need to check if another agent hit a problem, read `_agent_comms.json`.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T3.status = 'complete';
c.tasks.T3.completed = new Date().toISOString();
c.tasks.T3.exports = {
  class: 'FileQueue',
  path: 'simplebrain/ingest/queue.py',
  methods: ['enqueue(job)', 'dequeue() -> Optional[Job]', 'mark_failed(job, error)', 'complete(job)']
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T3 complete');
"
```

## Git Commit
When committing, only add YOUR files:
```bash
git add simplebrain/ingest/ tests/test_queue.py
git commit -m "feat: file-based job queue"
```

**Begin now.**
