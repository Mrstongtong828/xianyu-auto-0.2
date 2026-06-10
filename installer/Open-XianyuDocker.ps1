[CmdletBinding()]
param(
    [string]$Url = "http://127.0.0.1:8000",
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\XianyuDocker.Common.ps1"

try {
    if ($Help) {
        Show-XianyuLauncherHelp -Command "Open-XianyuDocker.ps1" -Summary "Open the Xianyu local admin URL in the default browser."
        exit 0
    }
    if ($DryRun) {
        Write-XianyuDryRun -Command "Open-XianyuDocker.ps1" -Url $Url
        Write-Host "Would open browser URL: $Url"
        exit 0
    }

    Set-XianyuUtf8
    Open-XianyuUrl -Url $Url
    exit 0
}
catch {
    Write-XianyuError $_.Exception.Message
    exit 1
}
