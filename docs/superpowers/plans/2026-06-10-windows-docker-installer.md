# Windows Docker Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a first-version Windows installer/launcher foundation that lets non-developer users run the project through Docker Desktop and later wrap the flow into a `.exe` installer.

**Architecture:** Keep the application in Docker. Add a small `installer/` layer that checks Docker, creates local runtime folders, generates `.env`, runs Docker Compose, opens the browser, and exposes service-management commands.

**Tech Stack:** Windows PowerShell/CMD, Docker Desktop, Docker Compose, FastAPI app container, optional future Inno Setup or NSIS wrapper.

---

## Confirmed Direction

The user accepts Docker Desktop as a prerequisite. Therefore this plan intentionally avoids a fragile single-file Python executable. The `.exe` should be a Windows-friendly wrapper around Docker orchestration, configuration, and service management.

## Target User Flow

1. User installs Docker Desktop.
2. User runs the future installer `.exe` or current script wrapper.
3. Installer checks Docker and Compose availability.
4. Installer creates `data`, `logs`, `backups`, and upload directories.
5. Installer creates `.env` if missing, prompts for `ADMIN_PASSWORD`, and generates `JWT_SECRET_KEY`.
6. Installer starts the stack with Docker Compose.
7. Installer waits for the health endpoint and opens `http://127.0.0.1:9000`.
8. User can later start, stop, restart, view logs, open the browser, or uninstall containers while keeping data by default.

## Subagent Assignments

Project-local `agents/*.toml` files were not found, so runtime built-in agents are used:

- `devops-engineer`: Docker installer flow and compose/env compatibility.
- `powershell-7-expert`: Windows PowerShell/CMD script robustness.
- `technical-writer`: Chinese end-user install and troubleshooting docs.

## Acceptance Criteria

- Installer scripts do not require modifying production Python or JavaScript.
- Scripts detect Docker Compose v2 (`docker compose`) and legacy `docker-compose`.
- Scripts never delete user data unless an explicit destructive flag is provided.
- `.env` generation does not store weak default admin secrets.
- The default app URL is localhost-only.
- Documentation explains Docker Desktop prerequisite and common failures.

## Verification Commands

- `powershell -NoProfile -ExecutionPolicy Bypass -File installer\install.ps1 -Help`
- `powershell -NoProfile -ExecutionPolicy Bypass -File installer\manage.ps1 -Help`
- `powershell -NoProfile -ExecutionPolicy Bypass -File installer\install.ps1 -DryRun`
- `powershell -NoProfile -ExecutionPolicy Bypass -File installer\manage.ps1 status -DryRun`

## Execution Result

Completed on 2026-06-10 with runtime built-in subagents:

- `devops-engineer`: created the first-version Docker Desktop based Windows installer/launcher foundation under `installer/`, plus installer contract tests.
- `powershell-7-expert`: hardened the PowerShell/CMD entrypoints for Docker Compose v2/legacy detection, non-destructive `.env` updates, explicit Docker Desktop install, safe uninstall, `-Help`, and `-DryRun`.
- `technical-writer`: added Chinese user-facing installer documentation and troubleshooting notes.

Actual entrypoints created:

- `installer\Install-XianyuDocker.ps1` / `installer\install.cmd`
- `installer\Start-XianyuDocker.ps1` / `installer\start.cmd`
- `installer\Stop-XianyuDocker.ps1` / `installer\stop.cmd`
- `installer\Status-XianyuDocker.ps1` / `installer\status.cmd`
- `installer\Logs-XianyuDocker.ps1` / `installer\logs.cmd`
- `installer\Open-XianyuDocker.ps1` / `installer\open.cmd`
- `installer\Uninstall-XianyuDocker.ps1` / `installer\uninstall.cmd`

Verification run by the main thread:

- `python -m unittest tests.installer_windows_launcher_unittest tests.deployment_security_unittest -v`: 11 tests passed.
- PowerShell AST parse check for all `installer/*.ps1`: passed.
- `docker compose -f .\docker-compose-cn.yml config --quiet`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\Install-XianyuDocker.ps1 -Help`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\Start-XianyuDocker.ps1 -DryRun -NoOpen`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\Status-XianyuDocker.ps1 -DryRun`: passed.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\Uninstall-XianyuDocker.ps1 -DryRun -RemoveData`: passed.

Known blocker:

- The real container start/build flow was not executed in this run because it can build images, start containers, open a browser, and modify local `.env`. Run `installer\install.cmd -NoOpen` on a Windows machine with Docker Desktop running to validate the full path.
