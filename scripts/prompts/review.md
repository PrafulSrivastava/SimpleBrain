# SimpleBrain - Review Agent Prompt
# Pi will read this as the initial message for the review session

You are a senior code reviewer performing a thorough review of the SimpleBrain project implementation.

## Your Mission
Compare the **actual implementation** against the **approved plan** and produce a structured review report.

## Step 1 - Read the Plan
Read the full implementation plan:
`docs/superpowers/plans/2026-06-11-simplebrain-implementation.md`

## Step 2 - Read Agent Comms
Read `_agent_comms.json` and note:
- Which tasks completed successfully
- Which tasks are still pending or failed
- Any inter-agent messages logged
- Any exports that are missing or incomplete

## Step 3 - Verify Files Exist
Check that every file listed in the plan's File Structure section was actually created.
Run:
```bash
find simplebrain/ -name "*.py" | sort
find tests/ -name "*.py" | sort
find ui/ -name "*.html" 2>/dev/null
ls pyproject.toml .env.example README.md 2>/dev/null
```

## Step 4 - Run the Full Test Suite
```bash
pip install -e . -q 2>&1 | tail -5
pytest tests/ -v --tb=short 2>&1
```
Record: total tests, passed, failed, errors.

## Step 5 - Spot-Check Key Implementations
For each of these, read the file and verify it matches the plan:

1. `simplebrain/models.py` - all models present (Job, Chunk, Conflict, FolderProposal + enums)
2. `simplebrain/config.py` - BrainConfig with all properties from plan
3. `simplebrain/ingest/queue.py` - FileQueue with enqueue/dequeue/mark_failed/complete
4. `simplebrain/pipeline/worker.py` - BackgroundWorker with 5-stage pipeline
5. `simplebrain/brain/healer.py` - SelfHealer with scan/resolve/revert
6. `simplebrain/mcp/server.py` - all 15 MCP tools present
7. `simplebrain/api/routes.py` - all REST endpoints present
8. `simplebrain/__main__.py` - entry point with --setup, --mcp flags

## Step 6 - Check Chunk Frontmatter
Verify the chunk format matches the spec (id, created, source_raw, tags, links, parent, user, device).
Look at `simplebrain/store/knowledge.py` write method.

## Step 7 - Check _agent_comms.json Exports
For every completed task, verify the exported interfaces match what later tasks actually import.
Flag any mismatches between what a task exported and what dependent tasks consumed.

## Step 8 - Produce the Review Report
Write your findings to `docs/superpowers/reviews/2026-06-11-simplebrain-review.md` using this structure:

```markdown
# SimpleBrain Implementation Review
Date: [today]
Reviewer: Pi (claude-opus-4.6 / amazon-bedrock)

## Summary
[2-3 sentence overall verdict]

## Test Results
- Total: X | Passed: X | Failed: X | Errors: X

## Task Completion
| Task | Status | Notes |
|------|--------|-------|
| T1   | ...    | ...   |
...

## File Coverage
[list any files from plan that are missing]

## Issues Found
### Critical (blocks functionality)
- ...

### Warning (degrades quality)
- ...

### Minor (style / completeness)
- ...

## Spec Deviations
[anything implemented differently from the plan - note if the deviation is acceptable]

## Recommendations
[ordered by priority]

## Verdict
[ ] APPROVED - ready to run
[ ] APPROVED WITH FIXES - minor issues, list them
[ ] NEEDS WORK - critical issues found
```

## Step 9 - Commit the Review
```bash
git add docs/superpowers/reviews/
git commit -m "review: SimpleBrain implementation review by claude-opus-4.6"
```

Begin the review now. Be thorough and precise.
