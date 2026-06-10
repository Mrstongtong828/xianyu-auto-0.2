[CmdletBinding()]
param(
    [string]$ProjectRoot,
    [string]$ComposeFile = "docker-compose-cn.yml",
    [switch]$NoBuild,
    [switch]$InstallDockerDesktop,
    [int]$DockerTimeoutSeconds = 240,
    [int]$HealthTimeoutSeconds = 180,
    [switch]$NoOpen,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\XianyuDocker.Common.ps1"

try {
    if ($Help) {
        Show-XianyuLauncherHelp -Command "Install-XianyuDocker.ps1" -Summary "Install or update the Xianyu Docker stack."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Install-XianyuDocker.ps1" -ComposeFile $ComposeFile
        Write-Host "Would prepare directories, create or update .env, build unless -NoBuild is set, start containers, wait for /health, and open the browser unless -NoOpen is set."
        exit 0
    }

    $context = Initialize-XianyuDockerEnvironment `
        -ProjectRoot $ProjectRoot `
        -ComposeFileName $ComposeFile `
        -InstallDockerDesktop:$InstallDockerDesktop `
        -DockerTimeoutSeconds $DockerTimeoutSeconds

    Start-XianyuDockerDeployment -Context $context -Build:(!$NoBuild)
    Wait-XianyuServiceHealth -Context $context -TimeoutSeconds $HealthTimeoutSeconds
    if (-not $NoOpen) {
        Open-XianyuUrl -Url $context.Url
    }
    Write-XianyuSuccess "Install/start complete. URL: $($context.Url)"
    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
