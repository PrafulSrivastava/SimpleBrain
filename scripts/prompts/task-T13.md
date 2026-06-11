# SimpleBrain - Agent Task: T13 - Setup Wizard

You are a Pi coding agent implementing **Task 13** of the SimpleBrain project.
You are running IN PARALLEL with agent T9. Your files do NOT overlap.

## Your Mission
Implement **Task 13: Setup Wizard** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` - check T8 exports for SelfGrower interface

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T2','T8'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T13.status = 'running';
c.tasks.T13.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T13 running');
"
```

## Your Task
Implement every step under `## Task 13: Setup Wizard` in the plan.

Files you own (ONLY touch these):
- `simplebrain/setup/__init__.py`
- `simplebrain/setup/wizard.py`
- `tests/test_setup.py`

## Parallel Agent Awareness
You are running alongside:
- **T9** -> working on `simplebrain/pipeline/worker.py`

No file overlap at all. Run independently.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T13.status = 'complete';
c.tasks.T13.completed = new Date().toISOString();
c.tasks.T13.exports = {
  class: 'SetupWizard',
  path: 'simplebrain/setup/wizard.py',
  methods: ['run(answers: dict) -> list[str]'],
  notes: 'answers dict keys: purpose, users, topics, healer_schedule, llm_provider, llm_model. Returns list of created folder names.'
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T13 complete');
"
```

## Git Commit
```bash
git add simplebrain/setup/ tests/test_setup.py
git commit -m "feat: setup wizard"
```

**Begin now.**
