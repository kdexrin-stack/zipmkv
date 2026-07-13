param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = [Drawing.Image]::FromFile((Resolve-Path -LiteralPath $SourcePath).Path)

function Write-SquareIcon([string]$Path, [int]$Size) {
    $directory = Split-Path -Parent $Path
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $bitmap = New-Object Drawing.Bitmap($Size, $Size)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.Clear([Drawing.Color]::White)
        $graphics.CompositingQuality = [Drawing.Drawing2D.CompositingQuality]::HighQuality
        $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.DrawImage($source, 0, 0, $Size, $Size)
        $bitmap.Save($Path, [Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

try {
    Write-SquareIcon (Join-Path $ProjectRoot 'store_assets\icon_1024.png') 1024
    Write-SquareIcon (Join-Path $ProjectRoot 'android\app\src\main\res\mipmap-mdpi\ic_launcher.png') 48
    Write-SquareIcon (Join-Path $ProjectRoot 'android\app\src\main\res\mipmap-hdpi\ic_launcher.png') 72
    Write-SquareIcon (Join-Path $ProjectRoot 'android\app\src\main\res\mipmap-xhdpi\ic_launcher.png') 96
    Write-SquareIcon (Join-Path $ProjectRoot 'android\app\src\main\res\mipmap-xxhdpi\ic_launcher.png') 144
    Write-SquareIcon (Join-Path $ProjectRoot 'android\app\src\main\res\mipmap-xxxhdpi\ic_launcher.png') 192
    Write-SquareIcon (Join-Path $ProjectRoot 'harmony\AppScope\resources\base\media\app_icon.png') 512
    Write-SquareIcon (Join-Path $ProjectRoot 'harmony\entry\src\main\resources\base\media\app_icon.png') 512
} finally {
    $source.Dispose()
}

Write-Host 'Application icon sizes generated.'
