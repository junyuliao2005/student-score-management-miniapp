# Codex Project Operating Rules

## Scope and authorization

Codex may read, create, modify, refactor, move, rename, and delete files inside this repository when required to complete project work. Normal code, test, documentation, migration-template, and configuration-template changes do not require per-file approval.

Codex must not modify files outside this repository, clear or rebuild an existing local/cloud database, delete cloud resources, expose or rotate real secrets, run destructive tests against production data, call paid APIs without explicit credentials and a bounded smoke-test request, or weaken backend authorization to make tests pass.

## Fixed architecture and product rules

- Keep the WeChat Mini Program + Flask + SQLAlchemy + MySQL architecture.
- Preserve `REQUEST_MODE=local|cloud`.
- Enforce student, parent, teacher, and admin boundaries on the backend.
- Students may only view the current logged-in student's published scores.
- Parents may only view published scores for actively bound children.
- Draft and withdrawn publications must never be returned to students or parents.
- Teacher access must evolve toward explicit class/course bindings; never silently grant school-wide access to legacy teachers.
- User-facing options come from database data; forms retain manual input plus selection.
- Excel imports require recognition/mapping, preview, validation, and explicit confirmation before writes.
- AI responses must label `real`, `mock`, or `fallback`; mock must never impersonate a real model.
- AI inputs must be privacy-sanitized. API keys stay in backend environment variables.
- Database changes use non-destructive migration scripts.

## Safety and quality rules

- Never print or commit `.env`, passwords, API keys, JWTs, Authorization headers, private keys, or database credentials.
- Use placeholders in examples and secret templates.
- Keep uploads outside public paths, use server-generated UUID names, validate content, and clean temporary files in `finally` blocks.
- Default tests use isolated SQLite/in-memory data and mocked external services.
- Do not claim external, cloud, Docker, OCR, or paid-AI verification unless it was actually run.
- Update tests and relevant documentation with each completed feature phase.

## Continuation protocol

At the start of a new session, read:

1. `AGENTS.md`
2. `docs/CODEX_AUTONOMOUS_PROGRESS.md`
3. `docs/NEXT_TASKS.md`
4. `docs/当前项目真实状态清单.md`

After each phase, update progress, executed commands, test results, unverified items, and Git status. If Git is unavailable, record that fact and provide exact manual commands instead of claiming a commit exists.

