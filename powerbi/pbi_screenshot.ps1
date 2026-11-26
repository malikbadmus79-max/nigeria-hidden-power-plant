# Open powerbi/report/HiddenPowerPlant.pbip in Power BI Desktop, wait for it to load, maximise, take a full-screen screenshot.
# Usage: powershell -File pbi_screenshot.ps1 -Out <png> [-WaitSeconds 60] [-NoOpen]
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$WaitSeconds = 60,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
}
"@
[void][Win]::SetProcessDPIAware()

if (-not $NoOpen) {
    Start-Process (Join-Path $PSScriptRoot 'report\HiddenPowerPlant.pbip')
    Start-Sleep -Seconds $WaitSeconds
}
$p = $null
for ($i = 0; $i -lt 24 -and -not $p; $i++) {
    $p = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if (-not $p) { Start-Sleep -Seconds 5 }
}
if (-not $p) { throw 'Power BI Desktop window not found' }
# If a "Do you want to save your changes?" dialog is showing, press Cancel (never Save).
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
$cond = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::NameProperty), 'Do you want to save your changes?'
$msg = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
if ($msg) {
    $bc = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::NameProperty), 'Cancel'
    $btn = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $bc)
    if ($btn) {
        $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        "save dialog found -> Cancel pressed"
        Start-Sleep -Seconds 3
    }
}
[void][Win]::ShowWindow($p.MainWindowHandle, 3)   # SW_MAXIMIZE
[Win]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [Win]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)   # Alt tap lets this process take the foreground
[void][Win]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep -Seconds 8
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
"saved $Out ($($b.Width)x$($b.Height)); window title: $($p.MainWindowTitle)"
