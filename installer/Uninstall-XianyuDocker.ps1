[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ProjectRoot,
    [string]$ComposeFile = "docker-compose-cn.yml",
    [switch]$RemoveImages,
    [switch]$RemoveData,
    [switch]$Force,
    [int]$DockerTimeoutSeconds = 60,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\XianyuDocker.Common.ps1"

try {
    if ($Help) {
        Show-XianyuLauncherHelp -Command "Uninstall-XianyuDocker.ps1" -Summary "Remove Xianyu Docker containers. Data is kept unless -RemoveData is specified."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Uninstall-XianyuDocker.ps1" -ComposeFile $ComposeFile
        Write-Host "Would run docker compose down. Would remove local data only if -RemoveData is specified and confirmed."
        exit 0
    }

    $context = Get-XianyuDockerContext `
        -ProjectRoot $ProjectRoot `
        -ComposeFileName $ComposeFile `
        -StartDockerDesktop `
        -DockerTimeoutSeconds $DockerTimeoutSeconds

    Push-Location -LiteralPath $context.ProjectRoot
    try {
        $args = @("down")
        if ($RemoveImages) {
            $args += @("--rmi", "local")
        }
        Invoke-XianyuCompose -Compose $context.Compose -ComposeFile $context.ComposeFile -Arguments $args | Out-Null
    }
    finally {
        Pop-Location
    }

    if ($RemoveData) {
        Remove-XianyuPersistentData -ProjectRoot $context.ProjectRoot -Force:$Force
        Write-XianyuWarning "Persistent data was removed because -RemoveData was specified."
    }
    else {
        Write-XianyuSuccess "Uninstalled containers/network only. Persistent data was kept."
    }

    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
