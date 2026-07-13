param(
    [Parameter(Mandatory = $true)]
    [string]$HapPath,
    [string]$HdcPath = ''
)

$ErrorActionPreference = 'Stop'
$resolvedHap = (Resolve-Path -LiteralPath $HapPath).Path
if ([IO.Path]::GetExtension($resolvedHap) -ne '.hap') {
    throw 'Only a .hap file can be installed. An Android APK is not a native HarmonyOS package.'
}

if (-not $HdcPath) {
    $command = Get-Command hdc -ErrorAction SilentlyContinue
    if ($command) {
        $HdcPath = $command.Source
    }
}
if (-not $HdcPath -or -not (Test-Path -LiteralPath $HdcPath -PathType Leaf)) {
    throw 'Official hdc was not found. Pass hdc.exe from the HarmonyOS SDK toolchains directory.'
}

$targets = & $HdcPath list targets
if ($LASTEXITCODE -ne 0 -or -not $targets) {
    throw 'No authorized HarmonyOS device was found. Connect a device and allow USB debugging.'
}

Write-Host 'Detected devices:'
$targets | ForEach-Object { Write-Host "  $_" }
& $HdcPath install -r $resolvedHap
if ($LASTEXITCODE -ne 0) {
    throw "HAP installation failed with exit code $LASTEXITCODE. Verify that the package has a valid device-compatible signature."
}
Write-Host 'HAP installed through hdc.'
