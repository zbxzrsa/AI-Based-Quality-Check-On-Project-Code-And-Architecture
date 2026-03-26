# Database Migration Policy

This project has legacy environments where schema objects may exist but
`alembic_version` is empty or inconsistent. To keep migration history
maintainable, use the workflow below.

## Standard flow (new databases)

1. Run `alembic upgrade head`.
2. For every schema change, create one migration and keep a single Alembic head.

## Reconcile legacy databases (existing schema)

If `alembic upgrade head` fails because tables already exist:

1. Make sure the current schema is backed up.
2. Reconcile history to current head:

```bash
python backend/tools/reconcile_alembic.py --force
```

3. Verify:

```bash
alembic current
alembic heads
```

Expected:
- `alembic current` points to the same revision as `alembic heads`.

## Docker commands

Run inside backend container:

```bash
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend \
  python /app/tools/reconcile_alembic.py --force
```

Then verify:

```bash
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend alembic current
docker exec -it ai_based_quality_check_on_project_code_and_architecture_backend alembic heads
```

## Guardrails

- Never delete business tables to "fix" migration history.
- Keep one head revision only.
- If a migration is superseded, mark it `.disabled` or replace via a new forward migration.
- Do not rewrite applied revisions in shared environments; create new migrations instead.
