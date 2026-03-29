# AGENTS.md

## Purpose
This repository uses Codex with milestone-based subagents. The goal is to turn a design doc into a scoped implementation plan, then execute milestones with isolated, reviewable changes.

## Global rules
- Follow the design doc as the source of truth unless a conflict with the codebase is found.
- Prefer small, reviewable diffs over large refactors.
- Do not make speculative architecture changes outside the assigned milestone.
- Preserve backward compatibility unless the milestone explicitly says otherwise.
- When uncertain, surface the issue clearly instead of guessing.

## Working style
- First understand the current code path before editing.
- Reuse existing abstractions and conventions where reasonable.
- Keep changes local to the smallest viable set of files.
- Update docs or comments when behavior changes materially.
- Add or update tests for any non-trivial behavior change.

## Planning requirements
When asked to plan from a design doc:
- Break work into 4-8 milestones.
- For each milestone include:
  - goal
  - dependencies
  - likely files/modules affected
  - implementation steps
  - risks / open questions
  - validation commands
  - acceptance criteria
- Explicitly mark which milestones are parallelizable and which must be sequential.

## Implementation requirements
When implementing a milestone:
- Only implement the assigned milestone.
- Avoid unrelated cleanup unless strictly required to complete the task.
- List all files changed and why.
- Run the milestone’s validation commands.
- Report blockers, tradeoffs, and remaining risks.

## Testing requirements
When testing a milestone:
- Verify happy path, edge cases, and likely regressions.
- Prefer the smallest set of tests that provides good confidence.
- If coverage is missing, add targeted tests.
- Report any untested risks explicitly.

## Review requirements
When reviewing a milestone:
- Check correctness
- Check edge cases
- Check API/schema compatibility
- Check whether scope expanded unnecessarily
- Check missing tests and docs
- Return concrete issues ranked by severity

## Output conventions
Unless the user asked otherwise, return:
1. Summary
2. Files touched
3. Validation run
4. Risks / blockers
5. Recommended next step

## Repository commands
Replace these with the real commands for this repo.

### Setup
- install: `make setup`

### Quality
- lint: `make lint`
- typecheck: `make typecheck`
- unit tests: `make test`
- integration tests: `make test-integration`

## Design doc location
Default design doc path:
- `docs/design.md`

## Milestone plan location
Default generated plan path:
- `plans/implementation-plan.md`

## Safety rails
- Do not edit secrets, CI, infra, or deployment files unless the milestone explicitly requires it.
- Do not rename public APIs without stating migration impact.
- Do not silently change schemas or wire formats.