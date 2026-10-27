# PEMS Audit & Development Playbook

Version 1.0 — 2026-10-28. This guide is based on prior audit notes; verify the current checkout before risky actions.

## Audit status
- **PASS**: the named check passed in recorded conditions.
- **FAIL**: the check found an issue.
- **NOT CHECKED**: evidence is missing.
- **RECHECK**: relevant code/config/dependencies/environment may have changed.
- **BLOCKED**: do not proceed until prerequisites or approval exist.

Avoid repeating checks when their inputs have not changed, but never skip required release checks. Record exact evidence and limitations.

## Mandatory safety
1. Do not modify `app/ton_validation.py` without explicit new instruction.
2. Preserve backups, audit reports, scripts, test candidates, untracked files, and user changes.
3. Never reset/delete/recreate the production database.
4. No production migration, admin bootstrap, or production import without approved plan, verified target, suitable backup, and explicit authorization.
5. No Git pull, merge, rebase, cherry-pick, commit, or push without explicit authorization for that operation.
6. No deployment without explicit authorization.
7. Prefer read-only inspection before changes.
8. Never print/request secrets, tokens, passwords, cookies, or `.env` contents.
9. During read-only audit, do not run data-changing database operations.
10. Give one terminal command at a time in interactive guidance.
11. Before significant changes, list affected files and verify backups.

## Historical project snapshot — not current verified state
- Local directory: `~/pems`
- Local branch: `integration/pems-github-sync`
- Recorded local HEAD: `8b22f4b` (`feat: integrate admin session auth and import hardening`)
- Recorded backup branch: `backup/pre-remote-sync-20261026`
- Remote branch: `origin/integration/pems-github-sync`
- Recorded remote HEAD: `c926f53` (PR #15 merge)
- Recorded common ancestor: `5ca58b5c85cda5384c9a097d332a7c9ad562123b`
- Recorded local divergence: ahead 1, behind 10
- Working tree previously included changes to `.fastapicloudignore`, `app/main.py`, and many untracked backups/reports/scripts/tests.
- PostgreSQL on `127.0.0.1:5432` previously accepted connections.
- `.env.local` was used; never print its contents.
- Last recorded deployment ID: `fafd3035-5e05-4e9d-bbdb-1ebb3f8596a2`; URL `https://pems-d85ae647.fastapicloud.dev`; app ID `bb02adac-372d-4e2c-abc8-b5a402da78f9`.

## Audit register from prior reports

| Area | Last reported status | Evidence | Recheck when |
|---|---|---|---|
| General local tests | PASS, historical | 77 passed in 3.13s | Relevant code/dependencies change or release checklist requires |
| Focused security/import tests | PASS, historical | 23 passed in 2.33s | Auth/import/routes/DB guard changes |
| Import guard tests | PASS, latest reported | Four files, 6 passed in 1.84s | Import service/routes, DB config, related tests change |
| Predeploy check | PASS, historical | `scripts/predeploy_check.py` with `PEMS_ENV=local PEMS_COOKIE_SECURE=true` | Deployment config or checked files change |
| Local PostgreSQL readiness | PASS, historical | `pg_isready` accepted connection | DB unavailable or DB tests needed |
| Git sync | NOT RESOLVED | Local/remote divergence and local changes recorded | Before any Git mutation |
| `app/ton_validation.py` | BLOCKED for edits | Local and remote precision/rounding behavior differed | Do not edit without explicit instruction |
| Remote import integrity/auth | RECHECK | Remote behavior differed from local hash/session protections | Before sync or release |
| Dashboard route auth | RECHECK | Remote previously differed in session dependencies | Before API/auth release |
| Local-only tests | RECHECK | Several local tests absent from remote listing | Before branch integration |
| Production periods | NOT CHECKED | Local changes/files were recorded | Before integration |

## Known technical findings

### Import authentication
Local code previously required a session user, `admin_utama` role, and CSRF. Remote previously accepted `PEMS_IMPORT_API_KEY` and a synthetic `legacy-api-key` user. Local tests expected legacy-key access to be rejected. Do not reconcile these behaviors without an explicit security decision.

### Import preview integrity
Local code previously hashed the staged file at preview and confirm, cached the preview, rejected changed files, and rejected blank `DATABASE_URL` before `psycopg.connect()`. Remote previously did not store the same hash/cache and defaulted to `postgresql:///pems_db` if `DATABASE_URL` was missing. The `import_confirm()` fallback for pending items lacking `preview`/`sha256` still needs review; do not assume vulnerability or remove it without checking lifecycle and compatibility.

Latest focused tests reported:
- `tests/test_import_database_url_guard.py`
- `tests/test_import_preview_integrity.py`
- `tests/test_import_preview_cache.py`
- `tests/test_import_preview_confirm_flow.py`
- Result: **6 passed in 1.84s**.

### Test inventory differences
Local previously included `test_auth_login_security.py`, `test_auth_logout_csrf.py`, `test_dashboard_auth.py`, `test_import_database_url_guard.py`, `test_import_preview_cache.py`, `test_import_preview_confirm_flow.py`, and `test_import_preview_integrity.py`. Remote previously listed `test_logout_csrf.py` instead of one logout test. Verify current files before deciding tests are missing.

### `app/ton_validation.py`
Local and remote previously differed in decimal precision and rounding. Do not edit or accidentally include that file in cherry-pick without explicit new instruction. Avoid cherry-picking a whole commit if it includes this file.

### Dashboard, production periods, packaging
Remote previously differed in session dependencies for `/api/summary`, `/api/estates`, and `/api/divisions`. Local production-period changes and `.fastapicloudignore` must be preserved and reviewed before integration.

## Efficient procedure
1. Inspect current Git branch/HEAD/status read-only and preserve all changes.
2. Select tests based on changed scope.
3. Auth/session/CSRF change → authentication/logout tests.
4. Import preview/confirm change → integrity/cache/confirm/cleanup/rollback/DB URL guard tests.
5. Dashboard/API change → API contract and route-auth tests.
6. Production-period change → production-period API tests.
7. Before release, run agreed release tests and predeploy check.
8. On failure, investigate before sync/deploy.
9. Record exact result, limitations, and next step.
10. Code changes: patch → compile/lint → focused tests → broader tests if needed → diff review.

## Next step from historical checkpoint
Latest reported action: four import-protection test files passed (`6 passed in 1.84s`). Next suggested read-only audit is comparing local and `origin/integration/pems-github-sync` versions of `app/auth.py`, `app/import_service.py`, and `app/import_routes.py`, after verifying current refs. Do not sync as part of the audit.

## Audit log template
Date; area; branch/commit; command/test; actual result; conclusion; limitations; status; reason to recheck; next step.

## Prompt for future sessions
“Continue PEMS using `AGENTS.md` and `docs/PEMS_AUDIT_PLAYBOOK.md`. Read `docs/PEMS_AUDIT_STATE.md` and `docs/PEMS_CHANGELOG_AUDIT.md`, verify current state, and continue unresolved findings. Do not repeat valid checks without relevant changes. Work read-only first and give one command at a time. Do not modify `app/ton_validation.py`, mutate Git branches/remotes, alter production data, or deploy without explicit approval.”
