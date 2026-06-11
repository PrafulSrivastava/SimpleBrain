# SimpleBrain - Agent Task: T8 - Pipeline File Stage

You are a Pi coding agent implementing **Task 8** of the SimpleBrain project.
You are running IN PARALLEL with agents T4 and T10. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 8: Pipeline File Stage** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` - check T7 exports for KnowledgeStore interface

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T2','T7'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T8.status = 'running';
c.tasks.T8.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T8 running');
"
```

## Your Task
Implement every step under `## Task 8: Pipeline - File Stage` in the plan.

Files you own (ONLY touch these):
- `simplebrain/pipeline/file.py`
- `simplebrain/brain/__init__.py`
- `simplebrain/brain/grower.py`
- `tests/test_file.py`

## Parallel Agent Awareness
You are running alongside:
- **T4** -> working on `simplebrain/store/raw.py` and `simplebrain/ingest/service.py`
- **T10** -> working on `simplebrain/brain/healer.py`

T10 also writes to `simplebrain/brain/` - you own `grower.py`, T10 owns `healer.py`. You both need `brain/__init__.py` - create it as an empty file. If T10 already created it, leave it as is.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T8.status = 'complete';
c.tasks.T8.completed = new Date().toISOString();
c.tasks.T8.exports = {
  classes: ['FileStage', 'SelfGrower'],
  paths: { FileStage: 'simplebrain/pipeline/file.py', SelfGrower: 'simplebrain/brain/grower.py' },
  methods: {
    FileStage: ['run(chunk) -> Tuple[Chunk, Optional[FolderProposal]]'],
    SelfGrower: ['get_folders() -> list[str]', 'create_proposal(folder, reasoning, chunk_id) -> FolderProposal', 'confirm_proposal(id) -> FolderProposal', 'reject_proposal(id) -> FolderProposal', 'list_pending() -> list[FolderProposal]']
  }
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T8 complete');
"
```

## Git Commit
```bash
git add simplebrain/pipeline/file.py simplebrain/brain/__init__.py simplebrain/brain/grower.py tests/test_file.py
git commit -m "feat: pipeline file stage and self-grower"
```

**Begin now.**
