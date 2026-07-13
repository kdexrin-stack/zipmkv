param(
    [string]$Version = "2.94.0"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ToolRoot = Join-Path $ProjectRoot "temp\github-cli"
$Archive = Join-Path $ToolRoot "gh.zip"
$Extracted = Join-Path $ToolRoot "gh_$Version`_windows_amd64"
$FlatExecutable = Join-Path $ToolRoot "bin\gh.exe"
$NestedExecutable = Join-Path $Extracted "bin\gh.exe"
$Url = "https://github.com/cli/cli/releases/download/v$Version/gh_$Version`_windows_amd64.zip"

New-Item -ItemType Directory -Force -Path $ToolRoot | Out-Null
if (-not (Test-Path $FlatExecutable) -and -not (Test-Path $NestedExecutable)) {
    Write-Host "Downloading project-local GitHub CLI $Version..."
    $client = New-Object System.Net.WebClient
    $client.DownloadFile($Url, $Archive)
    Expand-Archive -LiteralPath $Archive -DestinationPath $ToolRoot -Force
    Remove-Item -LiteralPath $Archive -Force
}

$Executable = if (Test-Path $FlatExecutable) { $FlatExecutable } else { $NestedExecutable }
& $Executable --version
