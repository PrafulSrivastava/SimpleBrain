# SimpleBrain — Agent Task: T5 — Pipeline Transcribe

You are a Pi coding agent implementing **Task 5** of the SimpleBrain project.
You are running IN PARALLEL with agents T3, T6, and T7. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 5: Pipeline — Transcribe** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — check T2 exports for BrainConfig, T1 exports for Job model

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
if (c.tasks.T2.status !== 'complete') { console.error('T2 not complete!'); process.exit(1); }
c.tasks.T5.status = 'running';
c.tasks.T5.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T5 running');
"
```

## Your Task
Implement every step under `## Task 5: Pipeline — Transcribe` in the plan.

Files you own (ONLY touch these):
- `simplebrain/pipeline/__init__.py`
- `simplebrain/pipeline/transcribe.py`
- `tests/test_transcribe.py`

## Parallel Agent Awareness
You are running alongside:
- **T3** → working on `simplebrain/ingest/queue.py`
- **T6** → working on `simplebrain/pipeline/chunk.py` and `tag.py`
- **T7** → working on `simplebrain/store/knowledge.py` and `index.py`

No overlap. Do not touch their files.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T5.status = 'complete';
c.tasks.T5.completed = new Date().toISOString();
c.tasks.T5.exports = {
  class: 'TranscribeStage',
  path: 'simplebrain/pipeline/transcribe.py',
  methods: ['run(job: Job) -> Job'],
  notes: 'Skips transcription for TEXT jobs. Uses module-level cached WhisperModel.'
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T5 complete');
"
```

## Git Commit
```bash
git add simplebrain/pipeline/__init__.py simplebrain/pipeline/transcribe.py tests/test_transcribe.py
git commit -m "feat: pipeline transcribe stage"
```

**Begin now.**
