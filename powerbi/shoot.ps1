# Go to report page N (0-4) via its bottom tab in Power BI Desktop and save a screenshot only when the page has
# finished rendering: (1) the page title is visible, then (2) two captures 5 s apart show the same canvas
# (no spinners or visuals still drawing), waiting at most 90 s. Writes the side-by-side compare (mockup on top)
# and optionally the cropped canvas.
param([Parameter(Mandatory = $true)][int]$Page, [Parameter(Mandatory = $true)][string]$Out,
      [string]$Canvas, [string]$Shot = "$env:TEMP\pbi_shot.png")
$here = $PSScriptRoot
$py = Join-Path $here "..\.venv\Scripts\python.exe"
$ui = Join-Path $here "pbi_ui.ps1"
$cmp = Join-Path $here "compare.py"
$prev = "$env:TEMP\pbi_shot_prev.png"
$tabs = @(268, 400, 586, 750, 887)          # x of the five page tabs (y 968) on the maximised 1920x1080 window
& $ui -X $tabs[$Page] -Y 968 -WaitMs 3000 | Out-Null

# 1. title visible
$ok = $false
for ($i = 0; $i -lt 8; $i++) {
    & $ui -X 1580 -Y 1060 -NoClick -WaitMs 2000 -Out $Shot | Out-Null
    & $py $cmp $Shot $Page "$env:TEMP\pbi_cmp_tmp.png" --check-title | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
}
if (-not $ok) { "page title never became visible"; exit 1 }

# 2. canvas stable: two captures 5 s apart identical (max 90 s)
$stable = $false
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt 90) {
    Copy-Item $Shot $prev -Force
    & $ui -X 1580 -Y 1060 -NoClick -WaitMs 5000 -Out $Shot | Out-Null
    & $py $cmp --same $prev $Shot
    if ($LASTEXITCODE -eq 0) { $stable = $true; break }
}
if (-not $stable) { "WARNING: page still changing after 90 s; saving the last capture" }

$args_ = @($Shot, $Page, $Out)
if ($Canvas) { $args_ += @("--canvas-only", $Canvas) }
& $py $cmp @args_
