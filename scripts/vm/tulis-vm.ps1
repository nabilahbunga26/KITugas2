# Ketik ke konsol VM BOB-ksi (butuh mks.enableRawKb = "FALSE" di bob-vm.vmx).
#   powershell -File scripts\vm\tulis-vm.ps1 -Text "root" -Enter -Klik
param([string]$Text = "", [switch]$Enter, [switch]$Klik)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern void SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rt,B; }
}
"@
Add-Type -AssemblyName System.Windows.Forms

$p = Get-Process vmware | Where-Object { $_.MainWindowTitle -like "*BOB-ksi*" } | Select-Object -First 1
if (-not $p) { Write-Host "jendela BOB-ksi tidak ditemukan"; exit 1 }
[void][W]::SetForegroundWindow($p.MainWindowHandle)
Start-Sleep -Milliseconds 400
if ($Klik) {
  $r = New-Object W+R
  [void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
  [W]::SetCursorPos(($r.L + [int](($r.Rt - $r.L) * 0.72)), ($r.T + [int](($r.B - $r.T) * 0.55)))
  Start-Sleep -Milliseconds 200
  [W]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
  [W]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 600
}
if ($Text) { [System.Windows.Forms.SendKeys]::SendWait($Text.Replace('{', '{{}').Replace('}', '{}}').Replace('+', '{+}').Replace('^', '{^}').Replace('%', '{%}').Replace('~', '{~}').Replace('(', '{(}').Replace(')', '{)}')) }
if ($Enter) { [System.Windows.Forms.SendKeys]::SendWait("{ENTER}") }
Write-Host "terkirim: $Text"
