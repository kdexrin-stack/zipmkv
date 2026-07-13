$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$required = @(
    'build-profile.json5',
    'AppScope\app.json5',
    'entry\src\main\module.json5',
    'entry\src\main\ets\entryability\EntryAbility.ets',
    'entry\src\main\ets\pages\Index.ets',
    'entry\src\main\ets\pages\RenamePage.ets',
    'entry\src\main\ets\pages\DanmakuPage.ets',
    'entry\src\main\ets\pages\SubtitlePage.ets'
)

foreach ($relative in $required) {
    $path = Join-Path $ProjectRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required project file is missing: $relative"
    }
}

$sourceFiles = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'entry\src\main\ets') -Recurse -Filter *.ets
$forbidden = @('BEGIN PRIVATE KEY', 'storePassword', 'keyPassword', 'profile:"', 'certpath')
foreach ($sourceFile in $sourceFiles) {
    $text = Get-Content -LiteralPath $sourceFile.FullName -Raw -Encoding utf8
    foreach ($pattern in $forbidden) {
        if ($text.Contains($pattern)) {
            throw "Possible private signing data was found in source: $($sourceFile.FullName)"
        }
    }
}

$pages = Get-Content -LiteralPath (Join-Path $ProjectRoot 'entry\src\main\resources\base\profile\main_pages.json') -Raw -Encoding utf8 | ConvertFrom-Json
foreach ($page in $pages.src) {
    $pageFile = Join-Path $ProjectRoot "entry\src\main\ets\$page.ets"
    if (-not (Test-Path -LiteralPath $pageFile -PathType Leaf)) {
        throw "Page manifest points to a missing file: $page"
    }
}

Write-Host "HarmonyOS source validation passed: $($sourceFiles.Count) ArkTS files."
