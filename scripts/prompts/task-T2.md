# SimpleBrain — Agent Task: T2 — BrainConfig

You are a Pi coding agent implementing **Task 2** of the SimpleBrain project.

## Your Mission
Implement **Task 2: BrainConfig** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read the comms file: `_agent_comms.json`
3. Check that T1 is marked `complete` in comms before proceeding

## Before You Start
Update `_agent_comms.json`:

```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
if (c.tasks.T1.status !== 'complete') { console.error('T1 not complete yet! Wait.'); process.exit(1); }
c.tasks.T2.status = 'running';
c.tasks.T2.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T2 running');
"
```

## Your Task
Implement every step under `## Task 2: BrainConfig` in the plan exactly as written.

This task creates:
- `simplebrain/config.py`
- `tests/test_config.py`

## After Completion

```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T2.status = 'complete';
c.tasks.T2.completed = new Date().toISOString();
c.tasks.T2.exports = {
  class: 'BrainConfig',
  path: 'simplebrain/config.py',
  properties: ['brain_root', 'user', 'device', 'llm_provider', 'llm_model', 'raw_audio_dir', 'raw_transcripts_dir', 'queue_dir', 'knowledge_dir', 'index_dir', 'conflicts_dir', 'meta_dir'],
  factory: 'BrainConfig.from_env()'
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T2 complete');
"
```

## Important Notes
- You are the ONLY agent in Wave 2
- T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13 all import BrainConfig — get the property names right
- The `config` fixture in conftest.py returns a `BrainConfig` — make sure your class matches what conftest expects

**Begin now.**
