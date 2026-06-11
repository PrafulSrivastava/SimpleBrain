# SimpleBrain - Agent Task: T4 - Raw Store & Ingest Service

You are a Pi coding agent implementing **Task 4** of the SimpleBrain project.
You are running IN PARALLEL with agents T8 and T10. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 4: Raw Store & Ingest Service** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` - check T3 exports for FileQueue interface, T2 exports for BrainConfig

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T2','T3'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T4.status = 'running';
c.tasks.T4.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T4 running');
"
```

## Your Task
Implement every step under `## Task 4: Raw Store & Ingest Service` in the plan.

Files you own (ONLY touch these):
- `simplebrain/store/__init__.py`
- `simplebrain/store/raw.py`
- `simplebrain/ingest/service.py`
- `tests/test_ingest.py`

## Parallel Agent Awareness
You are running alongside:
- **T8** -> working on `simplebrain/pipeline/file.py` and `simplebrain/brain/grower.py`
- **T10** -> working on `simplebrain/brain/healer.py`

No file conflicts. Check `_agent_comms.json` if you need to leave a message for another agent.

## If You Need to Send a Message to Another Agent
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.messages.push({ from: 'T4', to: 'T8', text: 'YOUR MESSAGE HERE', timestamp: new Date().toISOString() });
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
"
```

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T4.status = 'complete';
c.tasks.T4.completed = new Date().toISOString();
c.tasks.T4.exports = {
  classes: ['RawStore', 'IngestService'],
  paths: { RawStore: 'simplebrain/store/raw.py', IngestService: 'simplebrain/ingest/service.py' },
  methods: {
    IngestService: ['add_text_note(text, user, device) -> str', 'add_voice_note(bytes, filename, user, device) -> str'],
    RawStore: ['save_text(text, job_id) -> str', 'save_audio(bytes, filename, job_id) -> str', 'read_text(path) -> str']
  }
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T4 complete');
"
```

## Git Commit
```bash
git add simplebrain/store/raw.py simplebrain/store/__init__.py simplebrain/ingest/service.py tests/test_ingest.py
git commit -m "feat: raw store and ingest service"
```

**Begin now.**
