# SimpleBrain - Agent Task: T7 - Knowledge Store & Index Store

You are a Pi coding agent implementing **Task 7** of the SimpleBrain project.
You are running IN PARALLEL with agents T3, T5, and T6. Your files do NOT overlap with theirs.

## Your Mission
Implement **Task 7: Knowledge Store & Index Store** from the implementation plan.

## Files You Need to Read First
1. Read the full plan: `docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`
2. Read `_agent_comms.json` - check T2 exports for BrainConfig, T1 exports for Chunk model

## Before You Start
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
if (c.tasks.T2.status !== 'complete') { console.error('T2 not complete!'); process.exit(1); }
c.tasks.T7.status = 'running';
c.tasks.T7.started = new Date().toISOString();
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T7 running');
"
```

## Your Task
Implement every step under `## Task 7: Knowledge Store & Index Store` in the plan.

Files you own (ONLY touch these):
- `simplebrain/store/knowledge.py`
- `simplebrain/store/index.py`
- `tests/test_index.py`

Note: `simplebrain/store/__init__.py` may be created by T4 later. If it doesn't exist yet, create it as an empty file - safe to do.

## Parallel Agent Awareness
You are running alongside:
- **T3** -> working on `simplebrain/ingest/queue.py`
- **T5** -> working on `simplebrain/pipeline/transcribe.py`
- **T6** -> working on `simplebrain/pipeline/chunk.py` and `tag.py`

No overlap. T8 and T10 in Wave 4 will depend on your KnowledgeStore - make sure the interface is clean.

## After Completion
```bash
node -e "
const fs = require('fs');
const c = JSON.parse(fs.readFileSync('_agent_comms.json'));
c.tasks.T7.status = 'complete';
c.tasks.T7.completed = new Date().toISOString();
c.tasks.T7.exports = {
  classes: ['KnowledgeStore', 'IndexStore'],
  paths: { KnowledgeStore: 'simplebrain/store/knowledge.py', IndexStore: 'simplebrain/store/index.py' },
  methods: {
    KnowledgeStore: ['write(chunk, folder) -> Path', 'write_unfiled(chunk) -> Path', 'read(chunk_id) -> Chunk', 'update_links(chunk_id, links)'],
    IndexStore: ['update(chunk, path)', 'update_cross_links(chunks, knowledge_store)', 'search(query, tags) -> list[str]', 'load_tags() -> dict', 'load_topics() -> dict']
  }
};
fs.writeFileSync('_agent_comms.json', JSON.stringify(c, null, 2));
console.log('Comms updated: T7 complete');
"
```

## Git Commit
```bash
git add simplebrain/store/knowledge.py simplebrain/store/index.py tests/test_index.py
git commit -m "feat: knowledge store and index store"
```

**Begin now.**
