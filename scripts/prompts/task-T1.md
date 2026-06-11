# SimpleBrain - Agent Task: T1 - Project Scaffold & Core Models

You are a Pi coding agent implementing **Task 1** of the SimpleBrain project.

## Your Mission
Implement **Task 1: Project Scaffold & Core Models** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read the comms file: `_agent_comms.json`

## Before You Start
Update `_agent_comms.json` - set `tasks.T1.status` to `"running"` and `tasks.T1.started` to the current timestamp.

Use this exact bash command to update:
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T1.status = 'running';
c.tasks.T1.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T1 running');
"
```

## Your Task
Implement every step under `## Task 1: Project Scaffold & Core Models` in the plan exactly as written.

This task creates:
- `pyproject.toml`
- `simplebrain/__init__.py`
- `simplebrain/models.py`
- `tests/conftest.py`
- `.env.example`

## After Completion
1. Run the tests to confirm they pass
2. Commit your work as specified in the plan
3. Export key model names to comms so downstream agents know the interface:

```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T1.status = 'complete';
c.tasks.T1.completed = new Date().toISOString();
c.tasks.T1.exports = {
  models: ['Job', 'JobType', 'JobStatus', 'Chunk', 'Conflict', 'ConflictType', 'ConflictStatus', 'Resolution', 'FolderProposal', 'FolderProposalStatus'],
  models_path: 'simplebrain/models.py',
  conftest_path: 'tests/conftest.py',
  fixtures: ['brain_dir', 'config']
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T1 complete');
"
```

## Important Notes
- You are the ONLY agent in Wave 1 - no coordination needed
- All other tasks depend on this one - get models.py right
- Do not skip any steps in the plan
- The `conftest.py` fixtures (`brain_dir`, `config`) are used by every test file

**Begin now.**
