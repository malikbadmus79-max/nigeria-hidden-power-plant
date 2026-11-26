# Go to report page N (0-4) via its bottom tab in Power BI Desktop, move the pointer off the canvas, and save
# a screenshot only once the page title is visible (retries up to 8 times). Writes the side-by-side compare
# (mockup on top) and optionally the cropped canvas.
param([Parameter(Mandatory = $true)][int]$Page, [Parameter(Mandatory = $true)][string]$Out,
      [string]$Canvas, [string]$Shot = "$env:TEMP\pbi_shot.png")
$here = $PSScriptRoot
$py = Join-Path $here "..\.venv\Scripts\python.exe"
$tabs = @(268, 400, 586, 750, 887)          # x of the five page tabs (y 968) on the maximised 1920x1080 window
& (Join-Path $here "pbi_ui.ps1") -X $tabs[$Page] -Y 968 -WaitMs 4000 | Out-Null
for ($i = 0; $i -lt 8; $i++) {
    & (Join-Path $here "pbi_ui.ps1") -X 1580 -Y 1060 -NoClick -WaitMs 2500 -Out $Shot | Out-Null
    $args_ = @($Shot, $Page, $Out, "--check-title")
    if ($Canvas) { $args_ += @("--canvas-only", $Canvas) }
    & $py (Join-Path $here "compare.py") @args_
    if ($LASTEXITCODE -eq 0) { exit 0 }
}
"page title never became visible"; exit 1
