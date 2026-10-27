# Daftar semua jendela milik proses vmware.exe (buat nemuin jendela konsol VM, bukan dialog).
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public class E {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rt,B; }
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  public static List<IntPtr> Windows(uint target) {
    var list = new List<IntPtr>();
    EnumWindows((h, l) => {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid == target && IsWindowVisible(h)) { var r = new R(); GetWindowRect(h, out r);
        if ((r.Rt - r.L) > 100) list.Add(h); }
      return true; }, IntPtr.Zero);
    return list;
  }
}
"@
foreach ($p in Get-Process vmware -ErrorAction SilentlyContinue) {
  foreach ($h in [E]::Windows([uint32]$p.Id)) {
    $t = New-Object System.Text.StringBuilder 256; [void][E]::GetWindowText($h, $t, 256)
    $c = New-Object System.Text.StringBuilder 256; [void][E]::GetClassName($h, $c, 256)
    $r = New-Object E+R; [void][E]::GetWindowRect($h, [ref]$r)
    "{0} | class={1} | {2}x{3} | pid={4}" -f $t.ToString(), $c.ToString(), ($r.Rt-$r.L), ($r.B-$r.T), $p.Id
  }
}
