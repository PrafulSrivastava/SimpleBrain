# SimpleBrain — Agent Task: T9 — Background Worker

You are a Pi coding agent implementing **Task 9** of the SimpleBrain project.
You are running IN PARALLEL with agent T13. Your files do NOT overlap.

## Your Mission
Implement **Task 9: Background Worker** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — check ALL Wave 3 and Wave 4 task exports for interfaces

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T3','T4','T5','T6','T7','T8'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T9.status = 'running';
c.tasks.T9.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T9 running');
"
```

## Your Task
Implement every step under `## Task 9: Background Worker` in the plan.

Files you own (ONLY touch these):
- `simplebrain/pipeline/worker.py`
- `tests/test_worker.py`

## Key Interfaces to Use (from _agent_comms.json exports)
- `FileQueue` (T3): `enqueue`, `dequeue`, `mark_failed`, `complete`
- `TranscribeStage` (T5): `run(job) -> Job`
- `ChunkStage` (T6): `run(job) -> list[Chunk]`
- `TagStage` (T6): `run(chunk) -> Chunk`
- `FileStage` (T8): `run(chunk) -> Tuple[Chunk, Optional[FolderProposal]]`
- `IndexStore` (T7): `update(chunk, path)`, `update_cross_links(chunks, ks)`
- `KnowledgeStore` (T7): `read(chunk_id)`

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T9.status = 'complete';
c.tasks.T9.completed = new Date().toISOString();
c.tasks.T9.exports = {
  class: 'BackgroundWorker',
  path: 'simplebrain/pipeline/worker.py',
  methods: ['process_one() -> bool', 'run_forever(poll_interval=2.0)']
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T9 complete');
"
```

## Git Commit
```bash
git add simplebrain/pipeline/worker.py tests/test_worker.py
git commit -m "feat: background pipeline worker"
```

**Begin now.**
