param(
    [string]$Version = "3.44.6"
)

$ErrorActionPreference = "Stop"
$MobileRoot = Split-Path -Parent $PSScriptRoot
$ToolchainRoot = Join-Path $MobileRoot "toolchain"
$FlutterRoot = Join-Path $ToolchainRoot "flutter"
$Archive = Join-Path $ToolchainRoot "flutter_windows_$Version-stable.zip"
$ReleaseInfoUrl = "https://storage.googleapis.com/flutter_infra_release/releases/releases_windows.json"

New-Item -ItemType Directory -Force -Path $ToolchainRoot | Out-Null

if (-not (Test-Path (Join-Path $FlutterRoot "bin\flutter.bat"))) {
    if (Test-Path $FlutterRoot) {
        $resolvedToolchain = [System.IO.Path]::GetFullPath($ToolchainRoot).TrimEnd('\') + '\'
        $resolvedFlutter = [System.IO.Path]::GetFullPath($FlutterRoot).TrimEnd('\') + '\'
        if (-not $resolvedFlutter.StartsWith($resolvedToolchain, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove Flutter path outside the mobile toolchain."
        }
        Remove-Item -LiteralPath $FlutterRoot -Recurse -Force
    }
    $releases = Invoke-RestMethod $ReleaseInfoUrl
    $release = $releases.releases | Where-Object { $_.version -eq $Version -and $_.channel -eq "stable" } | Select-Object -First 1
    if (-not $release) {
        throw "Flutter stable $Version was not found in the official release index."
    }
    $downloadUrl = "https://storage.googleapis.com/flutter_infra_release/releases/$($release.archive)"
    Write-Host "Downloading Flutter $Version to project-local toolchain..."
    $client = New-Object System.Net.WebClient
    $client.DownloadFile($downloadUrl, $Archive)
    $actualHash = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLowerInvariant()
    if ($actualHash -ne $release.sha256.ToLowerInvariant()) {
        throw "Flutter archive checksum mismatch."
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath $ToolchainRoot -Force
    Remove-Item -LiteralPath $Archive -Force
}

& (Join-Path $FlutterRoot "bin\flutter.bat") config --no-analytics
& (Join-Path $FlutterRoot "bin\flutter.bat") --version
