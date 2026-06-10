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
        Show-XianyuLauncherHelp -Command "Stop-XianyuDocker.ps1" -Summary "Stop the Xianyu Docker stack without deleting data."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Stop-XianyuDocker.ps1" -ComposeFile $ComposeFile
        Write-Host "Would run docker compose down. Persistent data would be kept."
        exit 0
    }

    $context = Get-XianyuDockerContext `
        -ProjectRoot $ProjectRoot `
        -ComposeFileName $ComposeFile `
        -StartDockerDesktop `
        -DockerTimeoutSeconds $DockerTimeoutSeconds

    Stop-XianyuDockerDeployment -Context $context
    Write-XianyuSuccess "Service stopped. Persistent data was not deleted."
    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
