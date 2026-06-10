[CmdletBinding()]
param(
    [string]$ProjectRoot,
    [string]$ComposeFile = "docker-compose-cn.yml",
    [int]$DockerTimeoutSeconds = 60,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\XianyuDocker.Common.ps1"

try {
    if ($Help) {
        Show-XianyuLauncherHelp -Command "Status-XianyuDocker.ps1" -Summary "Show Docker container status and HTTP health."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Status-XianyuDocker.ps1" -ComposeFile $ComposeFile
        Write-Host "Would run docker compose ps and check /health without modifying local files."
        exit 0
    }

    $context = Get-XianyuDockerContext `
        -ProjectRoot $ProjectRoot `
        -ComposeFileName $ComposeFile `
        -StartDockerDesktop `
        -DockerTimeoutSeconds $DockerTimeoutSeconds

    Show-XianyuDockerStatus -Context $context
    if (Test-XianyuHttpHealth -Url $context.Url -TimeoutSeconds 10) {
        Write-XianyuSuccess "HTTP health check passed: $($context.Url)/health"
    }
    else {
        Write-XianyuWarning "HTTP health check failed or service is not ready: $($context.Url)/health"
        exit 2
    }
    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
