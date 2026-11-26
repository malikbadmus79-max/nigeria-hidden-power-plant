# UI step in Power BI Desktop: click (or drag from X,Y to X2,Y2), optionally type text, then screenshot.
# Acts only when a PBIDesktop window is the foreground window (checked before every input).
param([int]$X = -1, [int]$Y = -1, [int]$X2 = -1, [int]$Y2 = -1, [string]$Type, [switch]$Ctrl, [int]$Wheel = 0, [switch]$NoClick, [string]$Out,
      [int]$WaitMs = 2500)
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class U {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
    [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, IntPtr e);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
[void][U]::SetProcessDPIAware()
$p = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "HiddenPowerPlant*" } | Select-Object -First 1
if (-not $p) { $p = Get-Process PBIDesktop -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1 }
if (-not $p) { "no Power BI window"; exit 1 }
function Test-Fg { $fp = 0; [void][U]::GetWindowThreadProcessId([U]::GetForegroundWindow(), [ref]$fp); return $fp -eq $p.Id }
for ($i = 0; $i -lt 5 -and -not (Test-Fg); $i++) {
    [U]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [U]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)
    [void][U]::ShowWindow($p.MainWindowHandle, 3); [void][U]::SetForegroundWindow($p.MainWindowHandle)
    Start-Sleep -Milliseconds 700
}
if (-not (Test-Fg)) { "Power BI is not the foreground window; nothing sent"; exit 1 }
if ($X -ge 0) {
    [void][U]::SetCursorPos($X, $Y); Start-Sleep -Milliseconds 250
    if (-not (Test-Fg)) { "focus lost; nothing sent"; exit 1 }
    if ($Wheel -ne 0) { [U]::mouse_event(0x0800, 0, 0, [BitConverter]::ToUInt32([BitConverter]::GetBytes([int32]($Wheel * 120)), 0), [IntPtr]::Zero) }
  if (-not $NoClick) {
    if ($Ctrl) { [U]::keybd_event(0x11, 0, 0, [IntPtr]::Zero) }
    [U]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
    if ($X2 -ge 0) {   # drag in small steps so the drop target registers
        for ($k = 1; $k -le 20; $k++) {
            [void][U]::SetCursorPos([int]($X + ($X2 - $X) * $k / 20), [int]($Y + ($Y2 - $Y) * $k / 20)); Start-Sleep -Milliseconds 40
        }
        Start-Sleep -Milliseconds 300
    }
    [U]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
    if ($Ctrl) { [U]::keybd_event(0x11, 0, 2, [IntPtr]::Zero) }
  }
}
if ($Type) {
    Start-Sleep -Milliseconds 400
    if (-not (Test-Fg)) { "focus lost; text not typed"; exit 1 }
    [System.Windows.Forms.SendKeys]::SendWait($Type)
}
Start-Sleep -Milliseconds $WaitMs
if ($Out) {
    for ($i = 0; $i -lt 5 -and -not (Test-Fg); $i++) {   # another window came to the front: bring Power BI back
        [U]::keybd_event(0x12, 0, 0, [IntPtr]::Zero); [U]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)
        [void][U]::ShowWindow($p.MainWindowHandle, 3); [void][U]::SetForegroundWindow($p.MainWindowHandle)
        Start-Sleep -Milliseconds 2500
    }
    if (-not (Test-Fg)) { "Power BI is not the foreground window; no screenshot"; exit 1 }
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
    "saved $Out"
}
