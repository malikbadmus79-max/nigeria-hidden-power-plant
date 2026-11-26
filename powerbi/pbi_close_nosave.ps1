# Close Power BI Desktop WITHOUT saving (report files are written by build_pages.py while it is closed).
# Keys are sent only after checking that the foreground window belongs to PBIDesktop.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class K3 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
}
"@
[void][K3]::SetProcessDPIAware()
function Test-PbiForeground($procId) {
    $fg = [K3]::GetForegroundWindow(); $fp = 0; [void][K3]::GetWindowThreadProcessId($fg, [ref]$fp); return $fp -eq $procId
}
$p = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "HiddenPowerPlant*" } | Select-Object -First 1
if (-not $p) { "not running"; exit 0 }
[void]$p.CloseMainWindow()
if ($p.WaitForExit(8000)) { "closed (no prompt)"; exit 0 }
for ($i = 0; $i -lt 5; $i++) {
    [K3]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [K3]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)
    [void][K3]::ShowWindow($p.MainWindowHandle, 3); [void][K3]::SetForegroundWindow($p.MainWindowHandle)
    Start-Sleep -Milliseconds 700
    if (Test-PbiForeground $p.Id) { break }
}
if (-not (Test-PbiForeground $p.Id)) { "could not bring Power BI to the front; no keys sent"; exit 1 }
# Save dialog (centred on the maximised 1920x1080 window): click "Don't save"
[void][K3]::SetCursorPos(1044, 569); Start-Sleep -Milliseconds 300
if (-not (Test-PbiForeground $p.Id)) { "focus left Power BI; no click"; exit 1 }
[K3]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero); [K3]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
if ($p.WaitForExit(30000)) { "closed (Don't save)" } else { "still open"; exit 1 }
