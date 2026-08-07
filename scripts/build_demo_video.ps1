param(
    [string]$OutputPath = "demo/changesafe-demo.mp4"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$demoDir = Join-Path $repoRoot "demo"
$audioPath = Join-Path $demoDir "narration.wav"
$narrationPath = Join-Path $demoDir "narration.txt"
$resolvedOutput = Join-Path $repoRoot $OutputPath

New-Item -ItemType Directory -Force -Path $demoDir | Out-Null
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Rate = 0
$speaker.Volume = 100
$speaker.SetOutputToWaveFile($audioPath)
$speaker.Speak((Get-Content -Raw -LiteralPath $narrationPath))
$speaker.Dispose()

$durationText = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $audioPath
$duration = [double]::Parse($durationText, [Globalization.CultureInfo]::InvariantCulture)
$segment = [Math]::Round($duration / 3, 3)
$lastSegment = [Math]::Round($duration - (2 * $segment) + 0.1, 3)

$first = Join-Path $repoRoot "docs/screenshots/01-convergence.jpg"
$second = Join-Path $repoRoot "docs/screenshots/02-impact-and-migration.jpg"
$third = Join-Path $repoRoot "docs/screenshots/03-reviewed-and-recorded.jpg"
$filter = "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x07110f,setsar=1[v0];" +
          "[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x07110f,setsar=1[v1];" +
          "[2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x07110f,setsar=1[v2];" +
          "[v0][v1][v2]concat=n=3:v=1:a=0[v]"

& ffmpeg -y `
    -loop 1 -t $segment -i $first `
    -loop 1 -t $segment -i $second `
    -loop 1 -t $lastSegment -i $third `
    -i $audioPath `
    -filter_complex $filter `
    -map "[v]" -map "3:a" `
    -c:v libx264 -preset veryfast -crf 23 -r 30 -pix_fmt yuv420p `
    -c:a aac -b:a 160k -shortest `
    $resolvedOutput

if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg failed with exit code $LASTEXITCODE"
}

Write-Output $resolvedOutput
