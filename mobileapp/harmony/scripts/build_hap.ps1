param(
    [ValidateSet('debug', 'release')]
    [string]$BuildMode = 'debug',
    [string]$DevEcoToolsHome = $env:DEVECO_TOOLS_HOME,
    [string]$HarmonySdkHome = $env:DEVECO_SDK_HOME
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BuildProfile = Join-Path $ProjectRoot 'build-profile.json5'

function Resolve-Tool([string]$Name, [string[]]$Candidates) {
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

if (-not $HarmonySdkHome -or -not (Test-Path -LiteralPath $HarmonySdkHome -PathType Container)) {
    throw 'A real HarmonyOS SDK was not found. Install it with official DevEco tools and set DEVECO_SDK_HOME.'
}

$hvigor = Resolve-Tool 'hvigorw' @(
    (Join-Path $DevEcoToolsHome 'hvigor\bin\hvigorw.bat'),
    (Join-Path $DevEcoToolsHome 'hvigor\bin\hvigorw.cmd'),
    (Join-Path $ProjectRoot 'toolchain\command-line-tools\hvigor\bin\hvigorw.bat')
)
$ohpm = Resolve-Tool 'ohpm' @(
    (Join-Path $DevEcoToolsHome 'ohpm\bin\ohpm.bat'),
    (Join-Path $DevEcoToolsHome 'ohpm\bin\ohpm.cmd'),
    (Join-Path $ProjectRoot 'toolchain\command-line-tools\ohpm\bin\ohpm.bat')
)

if (-not $hvigor -or -not $ohpm) {
    throw 'Official Hvigor/ohpm tools were not found. Install Command Line Tools and set DEVECO_TOOLS_HOME.'
}

if ($BuildMode -eq 'release') {
    $profileText = Get-Content -LiteralPath $BuildProfile -Raw -Encoding utf8
    if ($profileText -match '"signingConfigs"\s*:\s*\[\s*\]') {
        throw 'Release signing is not configured. Configure your real certificate and Profile in DevEco Studio.'
    }
}

$env:DEVECO_SDK_HOME = (Resolve-Path -LiteralPath $HarmonySdkHome).Path
$env:OHPM_HOME = Split-Path -Parent (Split-Path -Parent $ohpm)

Write-Host "HarmonyOS SDK: $env:DEVECO_SDK_HOME"
Write-Host "ohpm: $ohpm"
Write-Host "Hvigor: $hvigor"

Push-Location $ProjectRoot
try {
    & $ohpm install --all
    if ($LASTEXITCODE -ne 0) {
        throw "ohpm install failed with exit code $LASTEXITCODE"
    }

    $debuggable = if ($BuildMode -eq 'debug') { 'true' } else { 'false' }
    & $hvigor --mode module -p product=default -p module=entry@default -p "debuggable=$debuggable" assembleHap --analyze=normal --no-daemon
    if ($LASTEXITCODE -ne 0) {
        throw "HAP build failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$haps = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'entry\build') -Recurse -Filter *.hap -ErrorAction SilentlyContinue
if (-not $haps) {
    throw 'Hvigor completed but no HAP output was found. Check the build log.'
}

$haps | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object {
    Write-Host "HAP generated: $($_.FullName)"
}
