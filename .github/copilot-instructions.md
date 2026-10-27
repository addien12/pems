# PEMS Agent Instructions

Before any PEMS audit or development, read `docs/PEMS_AUDIT_PLAYBOOK.md`, `docs/PEMS_AUDIT_STATE.md`, and `docs/PEMS_CHANGELOG_AUDIT.md`.

- Start with read-only inspection. Use recorded evidence to avoid repeating checks that remain valid.
- Repeat checks when relevant code, configuration, dependencies, or environment changes, or when required by a release checklist.
- State the exact test scope and results. Passing tests do not prove the entire production system is safe.
- Preserve backups, reports, untracked files, and all user changes.
- Do not modify `app/ton_validation.py` without a new explicit instruction from the project owner.
- Never reset, delete, or recreate the production database.
- No production migration, admin bootstrap, production import, Git pull/merge/rebase/cherry-pick/commit/push, or deployment without explicit authorization for that operation.
- Never print or request secrets, tokens, passwords, cookies, or `.env` contents.
- Prefer read-only checks before changes.
- Guide interactive terminal work one command at a time and wait for the user's output.
- Before edits, identify affected files and plan. Then patch, compile/lint as relevant, run focused tests, broaden tests if needed, and review the diff.
- Update `docs/PEMS_AUDIT_STATE.md` and append evidence to `docs/PEMS_CHANGELOG_AUDIT.md` after meaningful audits.
- Treat commits, branch status, test results, and environment notes as historical until verified in the current checkout.
