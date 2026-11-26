# Save the open HiddenPowerPlant project in Power BI Desktop (Ctrl+S) and optionally close it.
param([switch]$Close)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class K {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
}
"@
$p = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "HiddenPowerPlant*" } | Select-Object -First 1
if (-not $p) { "no HiddenPowerPlant window"; exit 0 }
[K]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [K]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)   # Alt tap
[void][K]::ShowWindow($p.MainWindowHandle, 3)
[void][K]::SetForegroundWindow($p.MainWindowHandle); Start-Sleep -Milliseconds 1000
[K]::keybd_event(0x1B, 0, 0, [IntPtr]::Zero); [K]::keybd_event(0x1B, 0, 2, [IntPtr]::Zero)   # Esc
Start-Sleep -Milliseconds 300
[K]::keybd_event(0x11, 0, 0, [IntPtr]::Zero); [K]::keybd_event(0x53, 0, 0, [IntPtr]::Zero)   # Ctrl+S
[K]::keybd_event(0x53, 0, 2, [IntPtr]::Zero); [K]::keybd_event(0x11, 0, 2, [IntPtr]::Zero)
Start-Sleep -Seconds 8
"saved"
if ($Close) {
    [void]$p.CloseMainWindow()
    if (-not $p.WaitForExit(30000)) { "still open (a dialog may be waiting)"; exit 1 }
    "closed"
}
