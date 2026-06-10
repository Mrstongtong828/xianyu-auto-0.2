# Shared helpers for the Xianyu Docker Desktop based Windows launcher.
# PowerShell 5.1-compatible syntax is used intentionally.

$script:XianyuDefaultComposeFile = "docker-compose-cn.yml"
$script:XianyuDefaultService = "xianyu-app"
$script:XianyuDefaultUrl = "http://127.0.0.1:8000"

function Set-XianyuUtf8 {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $script:OutputEncoding = $utf8NoBom
}

function Write-XianyuInfo {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[INFO] $Message"
}

function Write-XianyuSuccess {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "[OK] $Message"
}

function Write-XianyuWarning {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Warning $Message
}

function Write-XianyuError {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Error "[ERROR] $Message"
}

function Show-XianyuLauncherHelp {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string]$Summary = ""
    )

    Set-XianyuUtf8
    if (-not [string]::IsNullOrWhiteSpace($Summary)) {
        Write-Host $Summary
    }
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\installer\$Command"
    Write-Host ""
    Write-Host "Common options:"
    Write-Host "  -ProjectRoot <path>       Project root. Defaults to this repository."
    Write-Host "  -ComposeFile <file>       Compose file. Defaults to docker-compose-cn.yml."
    Write-Host "  -DryRun                  Print planned checks/actions without changing files or Docker state."
    Write-Host "  -Help                    Show this help."
}

function Write-XianyuDryRun {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string]$ComposeFile = "docker-compose-cn.yml",
        [string]$Url = "http://127.0.0.1:8000"
    )

    Set-XianyuUtf8
    Write-XianyuInfo "Dry run for $Command."
    Write-Host "Would check Docker CLI and Docker Compose availability."
    Write-Host "Would use compose file: $ComposeFile"
    Write-Host "Would use service URL: $Url"
    Write-Host "No files, containers, images, or environment values were changed."
}

function Resolve-XianyuProjectRoot {
    param([string]$ProjectRoot)

    if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
        $ProjectRoot = Split-Path -Parent $PSScriptRoot
    }

    $resolved = Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop
    return $resolved.ProviderPath
}

function Join-XianyuPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Child
    )
    return [System.IO.Path]::Combine($Root, $Child)
}

function Test-XianyuWindows {
    return ($env:OS -eq "Windows_NT" -or [System.IO.Path]::DirectorySeparatorChar -eq "\")
}

function Test-XianyuCommand {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-XianyuNative {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [switch]$IgnoreExitCode
    )

    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    if (-not $IgnoreExitCode -and $exitCode -ne 0) {
        throw "$FilePath $($Arguments -join ' ') failed with exit code $exitCode."
    }
    return $exitCode
}

function Get-XianyuComposeCommand {
    if (-not (Test-XianyuCommand -Name "docker")) {
        throw "Docker CLI was not found. Install Docker Desktop, start it, then retry."
    }

    & docker compose version *> $null
    if ($LASTEXITCODE -eq 0) {
        return New-Object psobject -Property @{
            FilePath = "docker"
            BaseArgs = @("compose")
            Display = "docker compose"
        }
    }

    if (Test-XianyuCommand -Name "docker-compose") {
        & docker-compose version *> $null
        if ($LASTEXITCODE -eq 0) {
            return New-Object psobject -Property @{
                FilePath = "docker-compose"
                BaseArgs = @()
                Display = "docker-compose"
            }
        }
    }

    throw "Docker Compose was not found. Docker Compose v2 ('docker compose') or legacy 'docker-compose' is required."
}

function Invoke-XianyuCompose {
    param(
        [Parameter(Mandatory = $true)]$Compose,
        [Parameter(Mandatory = $true)][string]$ComposeFile,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$IgnoreExitCode
    )

    $allArgs = @()
    $allArgs += $Compose.BaseArgs
    $allArgs += @("-f", $ComposeFile)
    $allArgs += $Arguments
    return Invoke-XianyuNative -FilePath $Compose.FilePath -Arguments $allArgs -IgnoreExitCode:$IgnoreExitCode
}

function Start-XianyuDockerDesktop {
    if (-not (Test-XianyuWindows)) {
        return
    }

    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path -LiteralPath $dockerDesktop) {
        Write-XianyuInfo "Starting Docker Desktop in the background."
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
    }
}

function Install-XianyuDockerDesktop {
    if (Test-XianyuCommand -Name "docker") {
        Start-XianyuDockerDesktop
        return
    }

    if (-not (Test-XianyuWindows)) {
        throw "Docker is not installed. Install Docker for this platform, then retry."
    }

    if (-not (Test-XianyuCommand -Name "winget")) {
        throw "Docker is not installed and winget was not found. Install Docker Desktop manually, then retry."
    }

    Write-XianyuInfo "Installing Docker Desktop with winget."
    Invoke-XianyuNative -FilePath "winget" -Arguments @(
        "install",
        "Docker.DockerDesktop",
        "--accept-package-agreements",
        "--accept-source-agreements"
    )
    Start-XianyuDockerDesktop
}

function Wait-XianyuDockerEngine {
    param([int]$TimeoutSeconds = 180)

    if (-not (Test-XianyuCommand -Name "docker")) {
        throw "Docker CLI was not found. Install Docker Desktop, start it, then retry."
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-XianyuSuccess "Docker engine is ready."
            return
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    throw "Docker engine did not become ready within $TimeoutSeconds seconds. Open Docker Desktop and check WSL/engine status."
}

function Read-EnvFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    $lines = [System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8)
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.TrimStart().StartsWith("#")) { continue }
        $index = $line.IndexOf("=")
        if ($index -le 0) { continue }
        $key = $line.Substring(0, $index).Trim()
        $value = $line.Substring($index + 1)
        if (-not [string]::IsNullOrWhiteSpace($key)) {
            $values[$key] = $value
        }
    }
    return $values
}

function Write-XianyuUtf8File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string[]]$Lines
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, ($Lines -join [Environment]::NewLine), $utf8NoBom)
}

function Format-XianyuEnvValue {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -match "[`r`n]") {
        throw "Environment values cannot contain line breaks."
    }

    if ($Value -match "^[A-Za-z0-9_./:@%+=,-]+$") {
        return $Value
    }

    $escaped = $Value.Replace("\", "\\").Replace('"', '\"')
    return '"' + $escaped + '"'
}

function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $formattedValue = Format-XianyuEnvValue -Value $Value
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = @([System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8))
    }

    $pattern = "^\s*" + [regex]::Escape($Key) + "\s*="
    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$formattedValue"
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $lines += "$Key=$formattedValue"
    }

    Write-XianyuUtf8File -Path $Path -Lines $lines
}

function Convert-XianyuSecureStringToPlainText {
    param([Parameter(Mandatory = $true)][securestring]$Value)

    $ptr = [IntPtr]::Zero
    try {
        $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        if ($ptr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        }
    }
}

function Read-XianyuAdminPassword {
    do {
        $securePassword = Read-Host "Create ADMIN_PASSWORD for the local admin account" -AsSecureString
        $plainPassword = Convert-XianyuSecureStringToPlainText -Value $securePassword
        if (-not [string]::IsNullOrWhiteSpace($plainPassword)) {
            return $plainPassword
        }
        Write-XianyuWarning "ADMIN_PASSWORD cannot be empty."
    } while ($true)
}

function New-XianyuRandomBase64Url {
    param(
        [int]$ByteCount = 32,
        [switch]$TrimPadding
    )

    $bytes = New-Object byte[] $ByteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }

    $value = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_")
    if ($TrimPadding) {
        $value = $value.TrimEnd("=")
    }
    return $value
}

function Ensure-XianyuEnvFile {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $envPath = Join-XianyuPath -Root $ProjectRoot -Child ".env"
    if (-not (Test-Path -LiteralPath $envPath)) {
        Write-XianyuInfo "Creating .env with generated secrets."
        Write-XianyuUtf8File -Path $envPath -Lines @(
            "# Generated by installer scripts. Do not commit this file."
        )
    }

    $envValues = Read-EnvFile -Path $envPath
    $changed = $false

    if (-not $envValues.ContainsKey("ADMIN_USERNAME")) {
        Set-EnvValue -Path $envPath -Key "ADMIN_USERNAME" -Value "admin"
        $changed = $true
    }
    if (-not $envValues.ContainsKey("ADMIN_PASSWORD")) {
        Set-EnvValue -Path $envPath -Key "ADMIN_PASSWORD" -Value (Read-XianyuAdminPassword)
        $changed = $true
    }
    if (-not $envValues.ContainsKey("JWT_SECRET_KEY")) {
        Set-EnvValue -Path $envPath -Key "JWT_SECRET_KEY" -Value (New-XianyuRandomBase64Url -ByteCount 48 -TrimPadding)
        $changed = $true
    }
    if (-not $envValues.ContainsKey("SECRET_ENCRYPTION_KEY")) {
        Set-EnvValue -Path $envPath -Key "SECRET_ENCRYPTION_KEY" -Value (New-XianyuRandomBase64Url -ByteCount 32)
        $changed = $true
    }
    if (-not $envValues.ContainsKey("DB_PATH")) {
        Set-EnvValue -Path $envPath -Key "DB_PATH" -Value "/app/data/xianyu_data.db"
        $changed = $true
    }
    if (-not $envValues.ContainsKey("TZ")) {
        Set-EnvValue -Path $envPath -Key "TZ" -Value "Asia/Shanghai"
        $changed = $true
    }

    if ($changed) {
        Write-XianyuSuccess "Updated missing .env values without replacing existing settings."
    }
    else {
        Write-XianyuInfo ".env already contains required values."
    }
}

function Ensure-XianyuDirectories {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $directories = @(
        "data",
        "logs",
        "backups",
        "static",
        "static/uploads",
        "static/uploads/images"
    )

    foreach ($directory in $directories) {
        $path = Join-XianyuPath -Root $ProjectRoot -Child $directory
        if (-not (Test-Path -LiteralPath $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
    Write-XianyuSuccess "Persistent directories are ready."
}

function Assert-XianyuProjectFiles {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$ComposeFileName
    )

    $required = @(
        $ComposeFileName,
        "entrypoint.sh",
        "global_config.yml"
    )

    if ($ComposeFileName -eq "docker-compose-cn.yml") {
        $required += "Dockerfile-cn"
    }

    foreach ($item in $required) {
        $path = Join-XianyuPath -Root $ProjectRoot -Child $item
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Required project file is missing: $item"
        }
    }
}

function Initialize-XianyuDockerEnvironment {
    param(
        [string]$ProjectRoot,
        [string]$ComposeFileName = $script:XianyuDefaultComposeFile,
        [switch]$InstallDockerDesktop,
        [int]$DockerTimeoutSeconds = 180
    )

    Set-XianyuUtf8
    $root = Resolve-XianyuProjectRoot -ProjectRoot $ProjectRoot
    Assert-XianyuProjectFiles -ProjectRoot $root -ComposeFileName $ComposeFileName
    Ensure-XianyuDirectories -ProjectRoot $root
    Ensure-XianyuEnvFile -ProjectRoot $root

    if ($InstallDockerDesktop) {
        Install-XianyuDockerDesktop
    }
    else {
        if (-not (Test-XianyuCommand -Name "docker")) {
            throw "Docker CLI was not found. Install Docker Desktop, start it, then retry."
        }
        Start-XianyuDockerDesktop
    }

    Wait-XianyuDockerEngine -TimeoutSeconds $DockerTimeoutSeconds
    $compose = Get-XianyuComposeCommand
    $composeFile = Join-XianyuPath -Root $root -Child $ComposeFileName

    return New-Object psobject -Property @{
        ProjectRoot = $root
        ComposeFile = $composeFile
        Compose = $compose
        Service = $script:XianyuDefaultService
        Url = $script:XianyuDefaultUrl
    }
}

function Get-XianyuDockerContext {
    param(
        [string]$ProjectRoot,
        [string]$ComposeFileName = $script:XianyuDefaultComposeFile,
        [switch]$StartDockerDesktop,
        [int]$DockerTimeoutSeconds = 60
    )

    Set-XianyuUtf8
    $root = Resolve-XianyuProjectRoot -ProjectRoot $ProjectRoot
    Assert-XianyuProjectFiles -ProjectRoot $root -ComposeFileName $ComposeFileName

    if (-not (Test-XianyuCommand -Name "docker")) {
        throw "Docker CLI was not found. Install Docker Desktop, start it, then retry."
    }

    if ($StartDockerDesktop) {
        Start-XianyuDockerDesktop
    }

    Wait-XianyuDockerEngine -TimeoutSeconds $DockerTimeoutSeconds
    $compose = Get-XianyuComposeCommand
    $composeFile = Join-XianyuPath -Root $root -Child $ComposeFileName

    return New-Object psobject -Property @{
        ProjectRoot = $root
        ComposeFile = $composeFile
        Compose = $compose
        Service = $script:XianyuDefaultService
        Url = $script:XianyuDefaultUrl
    }
}

function Start-XianyuDockerDeployment {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [switch]$Build
    )

    Push-Location -LiteralPath $Context.ProjectRoot
    try {
        $args = @("up", "-d")
        if ($Build) {
            $args += "--build"
        }
        Invoke-XianyuCompose -Compose $Context.Compose -ComposeFile $Context.ComposeFile -Arguments $args | Out-Null
    }
    finally {
        Pop-Location
    }
}

function Stop-XianyuDockerDeployment {
    param([Parameter(Mandatory = $true)]$Context)

    Push-Location -LiteralPath $Context.ProjectRoot
    try {
        Invoke-XianyuCompose -Compose $Context.Compose -ComposeFile $Context.ComposeFile -Arguments @("down") | Out-Null
    }
    finally {
        Pop-Location
    }
}

function Show-XianyuDockerStatus {
    param([Parameter(Mandatory = $true)]$Context)

    Push-Location -LiteralPath $Context.ProjectRoot
    try {
        Invoke-XianyuCompose -Compose $Context.Compose -ComposeFile $Context.ComposeFile -Arguments @("ps") | Out-Null
    }
    finally {
        Pop-Location
    }
}

function Show-XianyuDockerLogs {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [string]$Service = $script:XianyuDefaultService,
        [int]$Tail = 200,
        [switch]$Follow
    )

    $args = @("logs", "--tail", [string]$Tail)
    if ($Follow) {
        $args += "-f"
    }
    if (-not [string]::IsNullOrWhiteSpace($Service)) {
        $args += $Service
    }

    Push-Location -LiteralPath $Context.ProjectRoot
    try {
        Invoke-XianyuCompose -Compose $Context.Compose -ComposeFile $Context.ComposeFile -Arguments $args | Out-Null
    }
    finally {
        Pop-Location
    }
}

function Test-XianyuHttpHealth {
    param(
        [string]$Url = $script:XianyuDefaultUrl,
        [int]$TimeoutSeconds = 10
    )

    $healthUrl = $Url.TrimEnd("/") + "/health"
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec $TimeoutSeconds
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    }
    catch {
        if (Test-XianyuWindows -and (Test-XianyuCommand -Name "curl.exe")) {
            & curl.exe -fsS --max-time $TimeoutSeconds $healthUrl *> $null
            return ($LASTEXITCODE -eq 0)
        }
        return $false
    }
}

function Wait-XianyuServiceHealth {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-XianyuHttpHealth -Url $Context.Url -TimeoutSeconds 10) {
            Write-XianyuSuccess "Service health check passed: $($Context.Url)/health"
            return
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    Write-XianyuWarning "Service health check did not pass within $TimeoutSeconds seconds. Showing container status."
    Show-XianyuDockerStatus -Context $Context
    throw "Service did not become healthy at $($Context.Url)/health."
}

function Open-XianyuUrl {
    param([string]$Url = $script:XianyuDefaultUrl)

    if (Test-XianyuWindows) {
        Start-Process $Url | Out-Null
    }
    elseif (Test-XianyuCommand -Name "open") {
        Invoke-XianyuNative -FilePath "open" -Arguments @($Url) | Out-Null
    }
    elseif (Test-XianyuCommand -Name "xdg-open") {
        Invoke-XianyuNative -FilePath "xdg-open" -Arguments @($Url) | Out-Null
    }
    else {
        Write-XianyuInfo "Open this URL manually: $Url"
    }
}

function Test-XianyuPathUnderRoot {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $pathFull = [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    return $pathFull.StartsWith($rootFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
}

function Remove-XianyuPersistentData {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [switch]$Force
    )

    if (-not $Force) {
        $answer = Read-Host "This deletes local data/logs/backups/static uploads. Type DELETE to continue"
        if ($answer -ne "DELETE") {
            Write-XianyuInfo "Data deletion cancelled."
            return
        }
    }

    $targets = @(
        "data",
        "logs",
        "backups",
        "static/uploads"
    )

    foreach ($target in $targets) {
        $path = Join-XianyuPath -Root $ProjectRoot -Child $target
        if (-not (Test-Path -LiteralPath $path)) { continue }
        if (-not (Test-XianyuPathUnderRoot -Root $ProjectRoot -Path $path)) {
            throw "Refusing to remove path outside project root: $path"
        }
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}
