# Windows Docker Launcher Foundation

This folder contains the first-version Windows launcher script intended to be wrapped later by Inno Setup, NSIS, or another `.exe` installer shell.

## Operational Boundary

The launcher controls only this local path:

Windows PowerShell -> Docker Desktop -> `docker-compose-cn.yml` -> `xianyu-app` container -> `http://127.0.0.1:8000/health`

It does not install or modify Docker Desktop. If Docker is missing, it exits with an actionable error. If Docker Desktop is installed but the engine is stopped, it attempts to start Docker Desktop and waits for readiness.

## Run

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\Start-XianyuDocker.ps1
```

Useful installer-wrapper switches:

```powershell
powershell -ExecutionPolicy Bypass -File .\installer\Start-XianyuDocker.ps1 -Build
powershell -ExecutionPolicy Bypass -File .\installer\Start-XianyuDocker.ps1 -NoOpen
powershell -ExecutionPolicy Bypass -File .\installer\Install-XianyuDocker.ps1 -InstallDockerDesktop
```

## What It Does

- Checks `docker` and `docker compose version`.
- Waits for `docker info` to succeed.
- Creates `data`, `logs`, `backups`, `static`, `static/uploads`, and `static/uploads/images`.
- Creates or updates `.env` without replacing existing non-empty values.
- Prompts for `ADMIN_PASSWORD` when missing; it does not print the password.
- Generates `JWT_SECRET_KEY` and `SECRET_ENCRYPTION_KEY` when missing.
- Starts services with `docker compose -f docker-compose-cn.yml up -d`; pass `-Build` or use `Install-XianyuDocker.ps1` to rebuild.
- Waits for `http://127.0.0.1:8000/health`.
- Opens `http://127.0.0.1:8000`.

## Diagnostics

```powershell
docker compose -f docker-compose-cn.yml ps
docker compose -f docker-compose-cn.yml logs --tail=120 xianyu-app
curl.exe -v --max-time 10 http://127.0.0.1:8000/health
```

Wrapper command shortcuts are also available: `start.cmd`, `install.cmd`, `status.cmd`, `logs.cmd`, `stop.cmd`, `open.cmd`, and `uninstall.cmd`.

## Rollback

Stop the containers without deleting local persisted data:

```powershell
docker compose -f docker-compose-cn.yml down
```

Local runtime state remains in `data`, `logs`, `backups`, `static/uploads`, and `.env`.
