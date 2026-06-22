# CLAUDE.md

## Purpose

These are the operating instructions for Claude Code when working in this repository.

Treat this repository as a real production codebase. Reliability, clarity, maintainability, and disciplined execution are more important than speed, flashy UI, or broad unfinished implementation.

When there is a tradeoff between more features and a smaller reliable system, always choose the smaller reliable system.

---

## Core Operating Principles

1. Do not assume. Verify in the codebase.
2. Do not start coding before understanding the current repository structure and conventions.
3. Make surgical changes only.
4. Do not perform broad refactors unless explicitly requested.
5. Ask focused questions when a requirement is unclear.
6. For non-trivial work, write a short spec and implementation plan before coding.
7. For non-trivial work, wait for approval before implementation.
8. Write or update tests before or alongside implementation.
9. Run validation commands yourself before claiming completion.
10. Review your own work as if it is probably wrong.
11. Document important decisions so future sessions understand the reasoning.
12. If something cannot be verified, mark it explicitly as TODO. Do not invent names, fields, tables, APIs, or business rules.
13. If the requested scope becomes too large, build the smallest complete useful version and document remaining work.

---

## Before Touching Code

Before modifying files, inspect the existing codebase.

Check:

1. Folder structure
2. Package manager and lockfiles
3. `package.json` scripts
4. Framework conventions
5. Routing conventions
6. Component conventions
7. Database schema and migrations
8. Existing tests
9. Existing linting and formatting setup
10. Naming conventions
11. Environment variable patterns
12. Existing documentation

Do not assume any field name, table name, route, component pattern, API contract, or test convention unless it is verified in the repository.

If this is a new repository, create a minimal clean structure first, then treat that structure as the convention for future work.

---

## Handling Uncertainty

If a requirement is unclear and affects architecture, data model, UX flow, API behavior, MCP behavior, security, deletion, or business logic, stop and ask a focused question.

Ask one question at a time.

Prefer multiple-choice questions when possible.

Do not fill missing requirements with guesses.

If implementation can proceed safely with an explicit assumption, write the assumption in `DECISIONS.md` before coding.

If a field, table, API, route, or business rule cannot be verified, write a clear TODO in the relevant file or in `TODO.md`.

Use this format:

```md
TODO: Verify <specific thing> before relying on it.
Reason: <why this matters>
Impact: <what could break if this is wrong>
```

---

## Task Classification

Classify every task before starting.

### Trivial task

Examples:
- Small copy change
- Simple styling adjustment
- Fixing an obvious typo
- Updating one small documented value

Rules:
- No long plan required.
- Use the fastest adequate model.
- Keep the change surgical.
- Run the relevant focused check.

### Non-trivial task

Examples:
- New feature
- Database change
- API change
- MCP tool change
- Business logic change
- Authentication or permission change
- Significant UI flow change
- Refactor that affects multiple files

Rules:
- Write a short spec.
- Write a phased implementation plan.
- Identify tests.
- Ask for approval before coding.
- Implement in small verifiable steps.
- Run full validation before reporting completion.

### Large task

Examples:
- Multi-screen feature
- New app module
- Database plus UI plus MCP change
- Migration from one architecture to another
- Work spanning backend, frontend, tests, and documentation

Rules:
- Split into bounded work packages.
- Use focused passes or sub-agents where available.
- Keep each pass narrow: Backend, Frontend, DB, Tests, MCP, Documentation.
- Each pass should receive only the context it needs.
- Finish and validate one vertical slice before expanding.

---

## Required Spec for Non-Trivial Tasks

Before implementation, create or update a short spec in `SPEC.md`, `PROJECT_PLAN.md`, or another appropriate planning file.

The spec must include:

1. Goal
2. Scope
3. Out of scope
4. User flow or API flow
5. Data changes
6. UI changes
7. MCP changes, if relevant
8. Tests to add or update
9. Risks
10. Assumptions
11. Rollback or recovery considerations, if relevant

After writing the spec, present the plan and wait for approval.

Do not implement before approval unless the user explicitly instructs you to proceed without approval.

---

## Implementation Discipline

Make small, controlled changes.

Do:

1. Modify only files required for the task.
2. Prefer small vertical slices.
3. Keep business logic in reusable functions.
4. Keep UI components small and readable.
5. Avoid duplicated logic.
6. Use clear names.
7. Add comments only when they explain non-obvious reasoning.
8. Prefer boring, stable code over clever code.
9. Keep database access patterns consistent with the existing codebase.
10. Keep error handling consistent with the existing codebase.

Do not:

1. Perform broad refactors unless explicitly requested.
2. Rename unrelated files, functions, routes, fields, or tables.
3. Change formatting across unrelated files.
4. Introduce a new architecture without approval.
5. Add unnecessary dependencies.
6. Add paid services unless explicitly requested.
7. Add AI features unless explicitly requested.
8. Add tracking or external network calls unless explicitly requested.
9. Hide failures.
10. Claim something works without running checks.

If you notice unrelated problems, document them in `TODO.md` instead of fixing them immediately.

---

## Testing Requirements

Write tests before or alongside implementation.

At minimum, consider tests for:

1. Core business logic
2. Date handling
3. Timezone handling
4. Status transitions
5. Data validation
6. Filtering and sorting
7. API handlers
8. Database queries
9. MCP tools
10. Error paths
11. Empty states
12. Edge cases

For UI work, include practical verification steps even if automated UI tests are not available.

For every bug fix, add a regression test when feasible.

Do not present code as complete until relevant tests pass.

---

## Validation Commands

After each meaningful phase, run relevant checks.

Prefer the repository’s own scripts. If these scripts exist, use them:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

If the repository uses another package manager or different scripts, inspect and use the actual scripts.

If a command fails:

1. Stop.
2. Read the error.
3. Identify the root cause.
4. Fix the root cause.
5. Run the command again.
6. Document the fix if it affects future work.

Do not ignore failing tests, lint errors, type errors, or build errors.

Do not say the task is complete if validation did not run.

If validation cannot run because of missing dependencies, missing environment, or tool limitations, state that clearly and document the exact limitation.

---

## End-to-End Verification

For user-facing changes, verify the complete flow, not just isolated files.

Examples:

1. Can the app start?
2. Can the relevant page load?
3. Can the user complete the intended action?
4. Does the saved data persist?
5. Does the UI handle empty states?
6. Does the UI handle invalid input?
7. Does the API return the expected response?
8. Does the MCP tool return structured results?
9. Does the build pass?

Report only what was actually verified.

---

## Self-Review Requirement

After implementation and before final reporting, review the work under the assumption that it is wrong.

Look for:

1. Hidden bugs
2. Edge cases
3. Missing tests
4. Data model mistakes
5. Date and timezone issues
6. Error handling gaps
7. Security issues
8. Permissions issues
9. Hebrew and RTL issues
10. MCP safety issues
11. Unnecessary complexity
12. Unrelated changes
13. Incomplete documentation

Fix issues found during self-review before presenting the final result.

If an issue is real but out of scope, document it in `TODO.md`.

---

## Documentation Requirements

Keep documentation current.

For significant work, update or create:

1. `README.md`
2. `PROJECT_PLAN.md`
3. `ARCHITECTURE.md`
4. `DATA_MODEL.md`
5. `TEST_PLAN.md`
6. `DECISIONS.md`
7. `TODO.md`
8. `OPERATIONS.md`, if operational behavior changes
9. `CLAUDE_MCP_SETUP.md`, if MCP behavior changes

Do not regenerate documentation from scratch if only a small section changed.

Prefer concise updates that explain what changed and why.

---

## Decision Records

For non-trivial decisions, document the reasoning in `DECISIONS.md`.

Use this format:

```md
## YYYY-MM-DD: <Decision title>

### Decision
<What was decided>

### Context
<Why this decision was needed>

### Alternatives Considered
1. <Alternative A>
2. <Alternative B>

### Reason
<Why this approach was chosen>

### Consequences
<Tradeoffs, risks, and future implications>
```

Examples of decisions that should be documented:

1. Database design
2. MCP tool boundaries
3. API structure
4. Authentication approach
5. Framework choice
6. State management approach
7. Date/time handling
8. Export format
9. Large dependency additions
10. Any deviation from existing conventions

---

## TODO Discipline

Use TODOs only when something is genuinely unresolved or unverifiable.

A good TODO must include:

1. What needs to be verified or done
2. Why it matters
3. Where to check or who needs to decide
4. Impact if left unresolved

Do not use vague TODOs such as:

```md
TODO: fix later
```

Use clear TODOs such as:

```md
TODO: Verify whether action item owners should be free text or linked to Person records.
Reason: This affects filtering, MCP summaries, and future permissions.
Impact: Wrong choice may require data migration.
```

---

## Model Usage and Efficiency

Use model capability deliberately.

If Claude Code supports Opus Plan Mode, use it.

Preferred mode:

```text
opusplan
```

Expected behavior:

1. Use Opus for planning, architecture, data model decisions, MCP design, risk analysis, and final self-review.
2. Use Sonnet for implementation, routine coding, UI work, tests, lint fixes, and documentation updates.

Do not use the strongest model for every step.

Use the cheapest and fastest adequate model for each task.

### Model rules

For trivial changes:
- Use Sonnet only.
- Do not create a long plan.
- Do not involve sub-agents.

For non-trivial features:
- Use Opus for the short spec and implementation plan.
- Wait for approval.
- Use Sonnet for implementation.
- Use Sonnet to run and fix tests.
- Use Opus for final review if the change affects architecture, database, MCP, or business logic.

For large tasks:
- Use Opus to split the task into bounded work packages.
- Use focused implementation passes, preferably Sonnet, for Database, Backend, Frontend, MCP, Tests, and Documentation.
- Each pass should receive only the context it needs.

For debugging:
- Use Sonnet for simple failing tests or lint errors.
- Use Opus only when the root cause is unclear after inspection, or when the bug involves architecture, data flow, dates, concurrency, or MCP behavior.

For final review:
- Use Opus to review the finished change under the assumption that the implementation is wrong.

If `opusplan` or Opus is not available:
1. State that clearly.
2. Continue with Sonnet.
3. Compensate by writing a more explicit spec, smaller phases, and stronger tests.
4. Do not block the task just because Opus is unavailable.

---

## Context and Token Efficiency

Do not waste context.

1. Map the codebase once at the beginning.
2. Keep a short working summary in `PROJECT_PLAN.md` or `TODO.md`.
3. Use targeted file reads after the initial mapping.
4. Do not reread the entire repository repeatedly.
5. Do not include large unrelated files in context.
6. Do not paste full files into responses unless necessary.
7. Summarize findings before moving to the next phase.
8. Prefer small change batches.
9. Avoid rewriting generated files unless required.
10. Keep final reports concise and factual.

---

## Dependency Control

Before adding a dependency:

1. Check whether the project already has a suitable dependency.
2. Check whether the task can be solved cleanly without a new dependency.
3. Prefer stable, widely used packages.
4. Avoid dependencies that add major complexity.
5. Avoid paid SaaS dependencies unless explicitly requested.
6. Document why the dependency was added.

Do not add a UI framework, ORM, testing library, state manager, or external service without a clear reason.

---

## Security and Safety

Security rules:

1. Do not hardcode secrets.
2. Do not commit `.env` files.
3. Provide `.env.example` when environment variables are needed.
4. Validate all external input.
5. Avoid exposing stack traces in user-facing responses.
6. Do not add unnecessary network calls.
7. Do not add telemetry or tracking unless explicitly requested.
8. Do not create destructive operations unless explicitly requested.
9. For destructive operations, require explicit confirmation.
10. Document security assumptions.

For MCP tools:

1. Do not expose delete operations in MVP unless explicitly approved.
2. Do not expose bulk destructive updates.
3. Do not overwrite long text fields unless explicitly approved.
4. Validate all MCP inputs.
5. Return structured errors.
6. Prefer read-only tools unless write access is necessary.
7. Include IDs in responses when follow-up actions may be needed.
8. Make tool behavior predictable and narrow.

---

## Database Rules

For database work:

1. Inspect the existing schema first.
2. Do not guess table or field names.
3. Use migrations.
4. Keep migrations small and reversible when feasible.
5. Seed realistic test data when needed.
6. Test reset and seed flows.
7. Document assumptions in `DATA_MODEL.md`.
8. Consider indexes for fields used in filtering.
9. Be explicit about date storage format.
10. Avoid ambiguous date parsing.

If a migration could affect existing data, document the risk and ask for approval.

---

## Date and Time Rules

Date and time bugs are expensive.

Rules:

1. Store dates consistently.
2. Display dates according to the product requirement.
3. Be explicit about timezone assumptions.
4. Avoid ambiguous date parsing.
5. Test overdue calculations.
6. Test boundary cases such as today, tomorrow, yesterday, end of month, and missing due date.
7. Do not silently convert dates in ways that change meaning.

For Hebrew and Israeli business apps, display dates as:

```text
DD/MM/YYYY
```

Unless the repository specifies a different convention.

---

## Hebrew and RTL Requirements

When building Hebrew user interfaces:

1. Use `lang="he"` where appropriate.
2. Use `dir="rtl"` where appropriate.
3. Right-align forms and text by default.
4. Tables should feel natural in Hebrew.
5. Buttons, labels, empty states, and error messages should be in Hebrew.
6. Do not mix English UI labels unless the product explicitly requires it.
7. Test layouts with realistic Hebrew text.
8. Test mixed Hebrew and English text where relevant.
9. Avoid layouts that only work for short English strings.
10. Verify that visual order and tab order make sense for Hebrew users.

For Hebrew documents or generated Markdown intended for users, keep the text readable and naturally ordered.

---

## Accessibility

Use accessible UI patterns.

1. Use semantic HTML.
2. Connect labels to inputs.
3. Use buttons for actions.
4. Use links for navigation.
5. Ensure keyboard navigation works for main flows.
6. Do not rely only on color to communicate status.
7. Use clear error messages.
8. Avoid tiny clickable targets.
9. Maintain readable contrast.
10. Keep forms simple.

---

## Error Handling

Errors should be clear, structured, and useful.

For UI:
- Show clear Hebrew error messages.
- Do not expose stack traces.
- Provide recovery guidance where possible.

For APIs:
- Return structured errors.
- Use appropriate status codes.
- Validate input at boundaries.

For MCP:
- Return structured tool errors.
- Explain what failed.
- Do not pretend an action succeeded if it failed.

---

## Final Report Format

At the end of a task, provide a concise final report.

Include:

1. What was built or changed
2. Files changed
3. Tests added or updated
4. Validation commands run
5. Results of validation
6. What was not built
7. Known limitations
8. TODOs created
9. Decisions documented
10. Recommended next step

Do not claim that something passed if it was not run.

Use this format:

```md
## Final Report

### Completed
- ...

### Files Changed
- ...

### Tests
- ...

### Validation
- `npm run lint`: passed
- `npm run typecheck`: passed
- `npm run test`: passed
- `npm run build`: passed

### Not Included
- ...

### Known Limitations
- ...

### TODOs
- ...

### Decisions
- ...

### Recommended Next Step
- ...
```

---

## Definition of Done

A task is done only when:

1. The requested change exists.
2. The change is limited to the requested scope.
3. Relevant tests exist or a clear reason is given why they do not.
4. Relevant validation commands pass.
5. Documentation is updated when needed.
6. Important decisions are documented.
7. Known limitations are listed.
8. The implementation was self-reviewed.
9. No unrelated refactor was introduced.
10. The final report clearly states what was verified.

If any item is missing, do not present the task as fully complete.

---

## Default Behavioral Instruction

Work like a careful senior engineer.

Be direct.

Be precise.

Prefer verified facts over assumptions.

Prefer small working increments over broad unfinished work.

Prefer maintainable boring code over clever code.

When in doubt, stop, inspect, test, or ask one focused question.
