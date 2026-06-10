# Xianyu Optimization Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the most visible frontend defects and harden the highest-risk admin/security paths without broad rewrites.

**Architecture:** Keep the current FastAPI plus static frontend architecture. Apply bounded changes in three independent slices: frontend request/render hygiene, backend admin/security hardening, and regression coverage.

**Tech Stack:** FastAPI, plain JavaScript, Bootstrap, pytest/unittest-style tests, nginx, Docker Compose.

---

## Necessity Review

The following items are necessary now:

- Frontend encoding/request hygiene: necessary because `static/index.html` and `static/js/app.js` show visible mojibake, repeated manual Authorization headers, extensive debug logging, and many HTML injection points.
- Admin/session/pending-action resilience: necessary because `SESSION_TOKENS` and `pending_admin_actions` are in-memory process state, which is unsafe for restart or multi-worker operation.
- Trusted proxy handling: necessary because `X-Forwarded-For` is trusted directly in several paths, which can corrupt audit, captcha, and brute-force controls when the app is reachable without a trusted reverse proxy.
- Test coverage: necessary because existing tests already encode several target expectations, but local verification is currently blocked by missing `pytest`.

Deferred for later:

- Full frontend module split or bundler migration. This is valuable but too large for the current optimization pass.
- Full database-backed session store if it requires schema migration beyond the current safe window. A narrower adapter or explicit plan should come first.
- Large UI redesign. The immediate issue is correctness and maintainability, not visual overhaul.

## Agent Routing

Project-local `agents/*.toml` files were not found, so custom TOML role mapping is unavailable. Runtime built-in agents were used instead:

- `frontend-developer`: frontend request/render/encoding scope.
- `security-auditor`: backend admin/session/proxy hardening scope.
- `test-automator`: regression coverage and verification scope.

## Task 1: Frontend Request And Text Hygiene

**Files:**
- Modify: `static/index.html`
- Modify: `static/js/app.js`
- Test: `tests/static_html_text_encoding_unittest.py`
- Test: `tests/static_js_request_helper_unittest.py`

- [ ] Confirm all user-visible text in `static/index.html` remains valid UTF-8 Chinese.
- [ ] Keep Chart.js loading deterministic by either vendoring it under `static/lib/` or documenting and testing the external dependency.
- [ ] Route high-value API calls through `authenticatedFetch` or `safeFetch` rather than repeated manual Authorization objects.
- [ ] Replace debug-only `console.log` calls with a gated helper.
- [ ] Preserve existing behavior for dashboard, accounts, logs, orders, and item publish flows.
- [ ] Run `python -m pytest tests/static_html_text_encoding_unittest.py tests/static_js_request_helper_unittest.py -q`.

## Task 2: Admin Security Hardening

**Files:**
- Modify: `reply_server.py`
- Modify: `nginx/nginx.conf`
- Modify: `docker-compose.yml`
- Modify: `docker-compose-cn.yml`
- Test: `tests/reply_server_high_risk_auth_unittest.py`
- Test: `tests/deployment_security_unittest.py`
- Test: `tests/admin_pending_actions_unittest.py`

- [ ] Introduce a trusted proxy check before honoring `X-Forwarded-For`, `X-Forwarded-Proto`, or `X-Forwarded-Host`.
- [ ] Use the trusted client IP helper consistently in login, captcha, audit, and high-risk admin paths.
- [ ] Keep high-risk admin confirmation behavior compatible with existing pending action tests.
- [ ] Do not expose proxy passwords, cookies, tokens, or secrets in logs or API responses.
- [ ] Run `python -m pytest tests/reply_server_high_risk_auth_unittest.py tests/deployment_security_unittest.py tests/admin_pending_actions_unittest.py -q`.

## Task 3: Verification And Coverage

**Files:**
- Modify only under `tests/` unless production code has already been changed by the owning task.

- [ ] Confirm frontend tests cover UTF-8 text, request helper token injection, and auth-failure cleanup.
- [ ] Confirm backend tests cover high-risk pending action lifecycle and trusted proxy behavior.
- [ ] Add focused tests for any newly introduced helper functions.
- [ ] Run the smallest targeted test set first, then the broader relevant suite.

## Acceptance Criteria

- Frontend Chinese text is readable in source and rendered UI.
- API requests still attach Bearer tokens where required.
- Admin high-risk operations still require confirmation.
- Spoofed forwarded headers are ignored unless the direct client is trusted.
- Targeted tests pass in an environment with `pytest` installed.

## Execution Result

Completed on 2026-06-10 with runtime built-in subagents:

- `frontend-developer`: implemented the necessary frontend subset. `fetchJSON` now clears loading state in a `finally` block, dashboard issue-center session storage parsing tolerates invalid data, and issue actions are bound after render instead of inline `onclick`.
- `security-auditor`: implemented the necessary backend/deployment subset. Forwarded client IP headers are honored only from trusted proxy CIDRs, login/captcha/audit paths use the unified client IP helper, high-risk pending action mismatch no longer consumes valid pending actions, and Docker Compose app/VNC ports bind to localhost by default.
- `test-automator`: reviewed coverage and confirmed the relevant static/unit checks are present.

Verification run by the main thread:

- `python -m unittest tests.static_js_request_helper_unittest tests.static_html_text_encoding_unittest tests.frontend_http_smoke_unittest -v`: 10 tests passed.
- `python -m unittest tests.reply_server_high_risk_auth_unittest tests.deployment_security_unittest tests.admin_pending_actions_unittest tests.admin_health_summary_unittest -v`: 13 tests passed.
- `python -m py_compile reply_server.py tests\static_js_request_helper_unittest.py tests\reply_server_high_risk_auth_unittest.py tests\deployment_security_unittest.py tests\admin_pending_actions_unittest.py`: passed.
- `node --check static\js\app.js`: passed.

Known blockers:

- `pytest` is not installed in the available Python environments.
- Playwright is not installed, so browser-level smoke verification remains pending.
