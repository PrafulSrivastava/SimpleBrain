# SimpleBrain — Agent Task: T6 — Pipeline Chunk & Tag

You are a Pi coding agent implementing **Task 6** of the SimpleBrain project.
You are running IN PARALLEL with agents T3, T5, and T7. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 6: Pipeline — Chunk & Tag** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — check T2 exports for BrainConfig, T1 exports for Chunk model

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
if (c.tasks.T2.status !== 'complete') { console.error('T2 not complete!'); process.exit(1); }
c.tasks.T6.status = 'running';
c.tasks.T6.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T6 running');
"
```

## Your Task
Implement every step under `## Task 6: Pipeline — Chunk & Tag` in the plan.

Files you own (ONLY touch these):
- `simplebrain/pipeline/chunk.py`
- `simplebrain/pipeline/tag.py`
- `tests/test_chunk.py`
- `tests/test_tag.py`

Note: `simplebrain/pipeline/__init__.py` is owned by T5. If T5 already created it, do not modify it.
If T5 hasn't run yet, you may create it as an empty file — that's safe since it's just `pass`.

## Parallel Agent Awareness
You are running alongside:
- **T3** → working on `simplebrain/ingest/queue.py`
- **T5** → working on `simplebrain/pipeline/transcribe.py`
- **T7** → working on `simplebrain/store/knowledge.py` and `index.py`

No overlap. Check `_agent_comms.json` to see if T5 has finished `pipeline/__init__.py`.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T6.status = 'complete';
c.tasks.T6.completed = new Date().toISOString();
c.tasks.T6.exports = {
  classes: ['ChunkStage', 'TagStage'],
  paths: { ChunkStage: 'simplebrain/pipeline/chunk.py', TagStage: 'simplebrain/pipeline/tag.py' },
  methods: {
    ChunkStage: ['run(job: Job) -> list[Chunk]'],
    TagStage: ['run(chunk: Chunk) -> Chunk']
  },
  notes: 'ChunkStage uses litellm.completion. TagStage returns empty tags on JSON parse failure.'
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T6 complete');
"
```

## Git Commit
```bash
git add simplebrain/pipeline/chunk.py simplebrain/pipeline/tag.py tests/test_chunk.py tests/test_tag.py
git commit -m "feat: pipeline chunk and tag stages"
```

**Begin now.**
