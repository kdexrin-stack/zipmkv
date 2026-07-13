param(
    [Parameter(Mandatory = $true)]
    [string]$PubCache
)

$ErrorActionPreference = 'Stop'
$PluginRoot = Join-Path $PubCache 'hosted\pub.dev\flutter_open_chinese_convert-0.9.0'
$GradleFile = Join-Path $PluginRoot 'android\build.gradle'
if (-not (Test-Path -LiteralPath $GradleFile -PathType Leaf)) {
    throw "Expected Android plugin file was not found: $GradleFile"
}

$content = [IO.File]::ReadAllText($GradleFile)
$marker = '// zipmkv: AGP 9 uses built-in Kotlin.'
$kgpClasspath = '        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version")'
if ($content.Contains($kgpClasspath)) {
    $content = $content.Replace($kgpClasspath, '        // zipmkv: Kotlin is provided by AGP 9.')
}
$guard = 'def zipmkvIsAgp9OrAbove = com.android.Version.ANDROID_GRADLE_PLUGIN_VERSION.tokenize(''.'')[0].toInteger() >= 9'
if (-not $content.Contains($guard)) {
    $applyLine = 'apply plugin: "kotlin-android"'
    $replaceTarget = if ($content.Contains($applyLine)) { $applyLine } elseif ($content.Contains($marker)) { $marker } else { $null }
    if (-not $replaceTarget) {
        throw 'flutter_open_chinese_convert 0.9.0 has an unexpected Kotlin plugin declaration.'
    }
    $conditionalApply = @"
$marker
$guard
if (!zipmkvIsAgp9OrAbove) {
    apply plugin: "kotlin-android"
}
"@
    $content = $content.Replace($replaceTarget, $conditionalApply.TrimEnd())

    $kotlinOptions = @"
    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11
    }

"@
    if ($content.Contains($kotlinOptions)) {
        $content = $content.Replace($kotlinOptions, '')
    } elseif ($content.Contains('kotlinOptions {')) {
        throw 'flutter_open_chinese_convert 0.9.0 has an unexpected kotlinOptions block.'
    }
}
[IO.File]::WriteAllText($GradleFile, $content, [Text.UTF8Encoding]::new($false))

$FilePickerGradle = Join-Path $PubCache 'hosted\pub.dev\file_picker-11.0.2\android\build.gradle'
if (-not (Test-Path -LiteralPath $FilePickerGradle -PathType Leaf)) {
    throw "Expected file_picker Android plugin file was not found: $FilePickerGradle"
}
$filePickerContent = [IO.File]::ReadAllText($FilePickerGradle)
$filePickerKgp = '        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"'
if ($filePickerContent.Contains($filePickerKgp)) {
    $filePickerContent = $filePickerContent.Replace($filePickerKgp, '        // zipmkv: Kotlin is provided by AGP 9.')
    [IO.File]::WriteAllText($FilePickerGradle, $filePickerContent, [Text.UTF8Encoding]::new($false))
} elseif (-not $filePickerContent.Contains('// zipmkv: Kotlin is provided by AGP 9.')) {
    throw 'file_picker 11.0.2 has an unexpected Kotlin Gradle Plugin dependency.'
}

$LifecycleGradle = Join-Path $PubCache 'hosted\pub.dev\flutter_plugin_android_lifecycle-2.0.35\android\build.gradle.kts'
if (-not (Test-Path -LiteralPath $LifecycleGradle -PathType Leaf)) {
    throw "Expected lifecycle Android plugin file was not found: $LifecycleGradle"
}
$lifecycleContent = [IO.File]::ReadAllText($LifecycleGradle)
$lifecycleMarker = "    id(`"org.jetbrains.kotlin.android`")`r`n        .apply(false)"
if (-not $lifecycleContent.Contains($lifecycleMarker)) {
    $versionedMarker = '    id("org.jetbrains.kotlin.android") version "2.3.20" apply false'
    $singleLineMarker = '    id("org.jetbrains.kotlin.android") apply false'
    if ($lifecycleContent.Contains($versionedMarker) -or $lifecycleContent.Contains($singleLineMarker)) {
        $replaceMarker = if ($lifecycleContent.Contains($versionedMarker)) { $versionedMarker } else { $singleLineMarker }
        $lifecycleContent = $lifecycleContent.Replace($replaceMarker, $lifecycleMarker)
        [IO.File]::WriteAllText($LifecycleGradle, $lifecycleContent, [Text.UTF8Encoding]::new($false))
    } else {
    $androidPlugin = '    id("com.android.library")'
    if (-not $lifecycleContent.Contains($androidPlugin)) {
        throw 'flutter_plugin_android_lifecycle 2.0.35 has an unexpected plugins block.'
    }
    $lifecycleContent = $lifecycleContent.Replace($androidPlugin, "$androidPlugin`r`n$lifecycleMarker")
    [IO.File]::WriteAllText($LifecycleGradle, $lifecycleContent, [Text.UTF8Encoding]::new($false))
    }
}

Write-Host 'Android plugin compatibility patches are ready.'
