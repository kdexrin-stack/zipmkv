param(
    [switch]$SkipBootstrap,
    [switch]$SkipChecks
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ToolchainRoot = Join-Path $ProjectRoot 'toolchain'

if (-not $SkipBootstrap) {
    & (Join-Path $PSScriptRoot 'bootstrap_android_toolchain.ps1')
}

$java = Get-ChildItem -LiteralPath (Join-Path $ToolchainRoot 'jdk17') -Recurse -Filter java.exe | Select-Object -First 1
if (-not $java) {
    throw 'Project-local OpenJDK was not found.'
}
$env:JAVA_HOME = Split-Path -Parent (Split-Path -Parent $java.FullName)
$env:ANDROID_HOME = Join-Path $ToolchainRoot 'android-sdk'
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:GRADLE_USER_HOME = Join-Path $ToolchainRoot 'gradle-home'
$env:PUB_CACHE = Join-Path $ToolchainRoot 'pub-cache'
$env:TEMP = Join-Path $ToolchainRoot 'temp'
$env:TMP = $env:TEMP
$env:KOTLIN_DAEMON_RUN_FILES_PATH = Join-Path $ToolchainRoot 'kotlin-daemon'
[IO.Directory]::CreateDirectory($env:TEMP) | Out-Null
[IO.Directory]::CreateDirectory($env:KOTLIN_DAEMON_RUN_FILES_PATH) | Out-Null

$SigningRoot = Join-Path $ProjectRoot 'signing'
$KeyStore = Join-Path $SigningRoot 'android-release.p12'
$KeyProperties = Join-Path $ProjectRoot 'android\key.properties'
$KeyTool = Join-Path $env:JAVA_HOME 'bin\keytool.exe'

if (-not (Test-Path -LiteralPath $KeyStore -PathType Leaf)) {
    [IO.Directory]::CreateDirectory($SigningRoot) | Out-Null
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $password = [Convert]::ToBase64String($bytes).Replace('+', 'A').Replace('/', 'B').Replace('=', 'C')
    & $KeyTool -genkeypair -keystore $KeyStore -storetype PKCS12 -storepass $password -keypass $password -alias zipmkv -keyalg RSA -keysize 4096 -validity 10000 -dname 'CN=zipmkv Release, OU=Local Build, O=zipmkv, L=Local, ST=Local, C=CN'
    if ($LASTEXITCODE -ne 0) {
        throw "Android release key generation failed with exit code $LASTEXITCODE"
    }
    $storeFile = $KeyStore.Replace('\', '/')
    @(
        "storePassword=$password",
        "keyPassword=$password",
        'keyAlias=zipmkv',
        "storeFile=$storeFile"
    ) | Set-Content -LiteralPath $KeyProperties -Encoding ascii
}

if (-not (Test-Path -LiteralPath $KeyProperties -PathType Leaf)) {
    throw 'Android key.properties is missing. Restore it together with the release key before building updates.'
}

$Flutter = Join-Path $ToolchainRoot 'flutter\bin\flutter.bat'
Push-Location $ProjectRoot
try {
    & $Flutter pub get
    if ($LASTEXITCODE -ne 0) {
        throw "flutter pub get failed with exit code $LASTEXITCODE"
    }
    & (Join-Path $PSScriptRoot 'patch_android_plugins.ps1') -PubCache $env:PUB_CACHE
    if (-not $SkipChecks) {
        & $Flutter analyze
        if ($LASTEXITCODE -ne 0) {
            throw "flutter analyze failed with exit code $LASTEXITCODE"
        }
        & $Flutter test
        if ($LASTEXITCODE -ne 0) {
            throw "flutter test failed with exit code $LASTEXITCODE"
        }
    }
    & $Flutter build apk --release --target-platform android-arm64
    if ($LASTEXITCODE -ne 0) {
        throw "Flutter APK build failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

$SourceApk = Join-Path $ProjectRoot 'build\app\outputs\flutter-apk\app-release.apk'
$DistRoot = Join-Path $ProjectRoot 'dist'
[IO.Directory]::CreateDirectory($DistRoot) | Out-Null
$DistApk = Join-Path $DistRoot 'zipmkv-android-v1.0.0.apk'
Copy-Item -LiteralPath $SourceApk -Destination $DistApk -Force
$hash = (Get-FileHash -LiteralPath $DistApk -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "APK generated: $DistApk"
Write-Host "SHA256: $hash"
