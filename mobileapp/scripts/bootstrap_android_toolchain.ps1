$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ToolchainRoot = Join-Path $ProjectRoot 'toolchain'
$DownloadRoot = Join-Path $ToolchainRoot 'downloads'
$JdkRoot = Join-Path $ToolchainRoot 'jdk17'
$SdkRoot = Join-Path $ToolchainRoot 'android-sdk'
$CommandLineRoot = Join-Path $SdkRoot 'cmdline-tools\latest'
$CommandLineZip = Join-Path $DownloadRoot 'commandlinetools-win-14742923_latest.zip'
$JdkZip = Join-Path $DownloadRoot 'microsoft-jdk-17-windows-x64.zip'
$CommandLineUrl = 'https://dl.google.com/android/repository/commandlinetools-win-14742923_latest.zip'
$CommandLineSha1 = '16b3f45ddb3d85ea6bbe6a1c0b47146daf0db450'
$JdkUrl = 'https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip'

[IO.Directory]::CreateDirectory($DownloadRoot) | Out-Null
[IO.Directory]::CreateDirectory($JdkRoot) | Out-Null
[IO.Directory]::CreateDirectory($SdkRoot) | Out-Null

function Download-File([string]$Uri, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Write-Host "Downloading $Uri"
        Invoke-WebRequest -Uri $Uri -OutFile $Path
    }
}

Download-File $JdkUrl $JdkZip
$checksumText = (& curl.exe -L --fail --silent --show-error "$JdkUrl.sha256sum.txt") -join "`n"
if ($LASTEXITCODE -ne 0) {
    throw 'Could not download the official OpenJDK checksum file.'
}
$expectedJdkSha256 = ([regex]::Match($checksumText, '[A-Fa-f0-9]{64}')).Value.ToLowerInvariant()
$actualJdkSha256 = (Get-FileHash -LiteralPath $JdkZip -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not $expectedJdkSha256 -or $actualJdkSha256 -ne $expectedJdkSha256) {
    throw 'OpenJDK archive checksum validation failed.'
}

$java = Get-ChildItem -LiteralPath $JdkRoot -Recurse -Filter java.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $java) {
    & tar.exe -xf $JdkZip -C $JdkRoot
    if ($LASTEXITCODE -ne 0) {
        throw "OpenJDK extraction failed with exit code $LASTEXITCODE"
    }
    $java = Get-ChildItem -LiteralPath $JdkRoot -Recurse -Filter java.exe | Select-Object -First 1
}
if (-not $java) {
    throw 'OpenJDK extraction completed but java.exe was not found.'
}
$JavaHome = Split-Path -Parent (Split-Path -Parent $java.FullName)

Download-File $CommandLineUrl $CommandLineZip
$actualCommandLineSha1 = (Get-FileHash -LiteralPath $CommandLineZip -Algorithm SHA1).Hash.ToLowerInvariant()
if ($actualCommandLineSha1 -ne $CommandLineSha1) {
    throw 'Android command-line tools checksum validation failed.'
}

$sdkManager = Join-Path $CommandLineRoot 'bin\sdkmanager.bat'
if (-not (Test-Path -LiteralPath $sdkManager -PathType Leaf)) {
    $extractRoot = Join-Path $ToolchainRoot 'android-command-line-extracted'
    if (Test-Path -LiteralPath $extractRoot) {
        throw "Incomplete command-line tools directory already exists: $extractRoot"
    }
    [IO.Directory]::CreateDirectory($extractRoot) | Out-Null
    & tar.exe -xf $CommandLineZip -C $extractRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Android command-line tools extraction failed with exit code $LASTEXITCODE"
    }
    $extracted = Join-Path $extractRoot 'cmdline-tools'
    if (-not (Test-Path -LiteralPath (Join-Path $extracted 'bin\sdkmanager.bat'))) {
        throw 'Android command-line tools archive has an unexpected structure.'
    }
    [IO.Directory]::CreateDirectory((Split-Path -Parent $CommandLineRoot)) | Out-Null
    Copy-Item -LiteralPath $extracted -Destination $CommandLineRoot -Recurse
}

$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $SdkRoot
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:GRADLE_USER_HOME = Join-Path $ToolchainRoot 'gradle-home'
$env:PUB_CACHE = Join-Path $ToolchainRoot 'pub-cache'
$env:TEMP = Join-Path $ToolchainRoot 'temp'
$env:TMP = $env:TEMP
[IO.Directory]::CreateDirectory($env:GRADLE_USER_HOME) | Out-Null
[IO.Directory]::CreateDirectory($env:PUB_CACHE) | Out-Null
[IO.Directory]::CreateDirectory($env:TEMP) | Out-Null

$licenseInput = (1..30 | ForEach-Object { 'y' }) -join [Environment]::NewLine
$licenseInput | & $sdkManager --sdk_root=$SdkRoot --licenses | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Android SDK license acceptance failed with exit code $LASTEXITCODE"
}

& $sdkManager --sdk_root=$SdkRoot 'platform-tools' 'platforms;android-36' 'build-tools;36.0.0' 'ndk;28.2.13676358'
if ($LASTEXITCODE -ne 0) {
    throw "Android SDK component installation failed with exit code $LASTEXITCODE"
}

$Flutter = Join-Path $ToolchainRoot 'flutter\bin\flutter.bat'
& $Flutter config --android-sdk $SdkRoot
if ($LASTEXITCODE -ne 0) {
    throw "Flutter Android SDK configuration failed with exit code $LASTEXITCODE"
}

Write-Host "JAVA_HOME=$JavaHome"
Write-Host "ANDROID_SDK_ROOT=$SdkRoot"
Write-Host 'Android toolchain bootstrap completed.'
