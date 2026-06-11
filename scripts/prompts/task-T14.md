# SimpleBrain — Agent Task: T14 — Entry Point & README

You are a Pi coding agent implementing **Task 14** of the SimpleBrain project.
You are the FINAL agent — all prior waves are complete.

## Your Mission
Implement **Task 14: Entry Point & README** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` — review ALL task exports to understand the full interface landscape before writing the entry point
3. Read the existing source files to understand what has been built

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
const prereqs = ['T9','T11','T12','T13'];
const missing = prereqs.filter(t => c.tasks[t].status !== 'complete');
if (missing.length) { console.error('Prerequisites not complete: ' + missing.join(', ')); process.exit(1); }
c.tasks.T14.status = 'running';
c.tasks.T14.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T14 running');
"
```

## Your Task
Implement every step under `## Task 14: Entry Point & README` in the plan.

Files you own:
- `simplebrain/__main__.py`
- `README.md`

## Final Full Test Suite
After implementing, run the full test suite:
```bash
pytest tests/ -v --tb=short
```

All tests must pass. If any fail, investigate and fix before completing.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T14.status = 'complete';
c.tasks.T14.completed = new Date().toISOString();
c.tasks.T14.exports = {
  entrypoint: 'python -m simplebrain',
  flags: ['--setup (run setup wizard)', '--mcp (stdio MCP server)', '--host', '--port'],
  notes: 'All 14 tasks complete. SimpleBrain v0.1.0 ready.'
};
c.shared_context.build_complete = true;
c.shared_context.completed_at = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('SimpleBrain build complete!');
"
```

## Git Commit
```bash
git add simplebrain/__main__.py README.md _agent_comms.json
git commit -m "feat: entry point and README — SimpleBrain v0.1.0 complete"
```

**Begin now.**
