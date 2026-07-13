$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$FontDirectory = Join-Path $ProjectRoot 'toolchain\fonts'
$FontPath = Join-Path $FontDirectory 'NotoSansCJKsc-Regular.otf'
$FontUrl = 'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
$Flutter = Join-Path $ProjectRoot 'toolchain\flutter\bin\flutter.bat'

if (-not (Test-Path -LiteralPath $Flutter -PathType Leaf)) {
    throw 'Project-local Flutter was not found. Run bootstrap_flutter.ps1 first.'
}

if (-not (Test-Path -LiteralPath $FontPath -PathType Leaf)) {
    [IO.Directory]::CreateDirectory($FontDirectory) | Out-Null
    Write-Host 'Downloading the official open-source Noto CJK font for screenshot rendering...'
    Invoke-WebRequest -Uri $FontUrl -OutFile $FontPath
}

Push-Location $ProjectRoot
try {
    & $Flutter test tool\capture_store_screenshots_test.dart --update-goldens
    if ($LASTEXITCODE -ne 0) {
        throw "Screenshot rendering failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host 'Store screenshots generated in store_assets/screenshots.'
