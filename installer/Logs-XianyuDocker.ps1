[CmdletBinding()]
param(
    [string]$ProjectRoot,
    [string]$ComposeFile = "docker-compose-cn.yml",
    [string]$Service = "xianyu-app",
    [int]$Tail = 200,
    [switch]$Follow,
    [int]$DockerTimeoutSeconds = 60,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\XianyuDocker.Common.ps1"

try {
    if ($Help) {
        Show-XianyuLauncherHelp -Command "Logs-XianyuDocker.ps1" -Summary "Show Docker logs for the Xianyu app service."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Logs-XianyuDocker.ps1" -ComposeFile $ComposeFile
        Write-Host "Would run docker compose logs --tail=$Tail for service '$Service'."
        exit 0
    }

    $context = Get-XianyuDockerContext `
        -ProjectRoot $ProjectRoot `
        -ComposeFileName $ComposeFile `
        -StartDockerDesktop `
        -DockerTimeoutSeconds $DockerTimeoutSeconds

    Show-XianyuDockerLogs -Context $context -Service $Service -Tail $Tail -Follow:$Follow
    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
