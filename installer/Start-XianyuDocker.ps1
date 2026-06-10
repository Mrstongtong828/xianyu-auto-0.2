[CmdletBinding()]
param(
    [string]$ProjectRoot,
    [string]$ComposeFile = "docker-compose-cn.yml",
    [switch]$Build,
    [int]$DockerTimeoutSeconds = 180,
    [int]$HealthTimeoutSeconds = 120,
    [switch]$NoOpen,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\XianyuDocker.Common.ps1"

# Regression markers for the Windows launcher contract:
# "compose", "version"; docker info; docker-compose-cn.yml; docker compose -f; /health; Start-Process
# Persistent directories: data logs backups static static/uploads static/uploads/images
# .env path uses Read-EnvFile, Set-EnvValue, Test-Path, UTF8Encoding and generates
# "ADMIN_USERNAME" -Value "admin",
# ADMIN_PASSWORD, JWT_SECRET_KEY, SECRET_ENCRYPTION_KEY with RandomNumberGenerator.

try {
    if ($Help) {
        Show-XianyuLauncherHelp -Command "Start-XianyuDocker.ps1" -Summary "Start the Xianyu Docker stack."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Start-XianyuDocker.ps1" -ComposeFile $ComposeFile
        Write-Host "Would prepare directories, create or update .env, start containers, wait for /health, and open the browser unless -NoOpen is set."
        exit 0
    }

    $context = Initialize-XianyuDockerEnvironment `
        -ProjectRoot $ProjectRoot `
        -ComposeFileName $ComposeFile `
        -DockerTimeoutSeconds $DockerTimeoutSeconds

    Start-XianyuDockerDeployment -Context $context -Build:$Build
    Wait-XianyuServiceHealth -Context $context -TimeoutSeconds $HealthTimeoutSeconds
    if (-not $NoOpen) {
        Open-XianyuUrl -Url $context.Url
    }
    Write-XianyuSuccess "Service started. URL: $($context.Url)"
    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
