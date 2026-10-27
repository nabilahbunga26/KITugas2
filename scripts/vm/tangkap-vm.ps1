# Tangkap jendela konsol VM jadi PNG (buat memastikan Alpine sudah boot).
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Drawing;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rt,B; }
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  public static Bitmap Capture(IntPtr h, int w, int hd) {
    var bmp = new Bitmap(w, hd);
    using (var g = Graphics.FromImage(bmp)) {
      IntPtr dc = g.GetHdc();
      PrintWindow(h, dc, 2);   // PW_RENDERFULLCONTENT: bisa merekam jendela yang tertutup
      g.ReleaseHdc(dc);
    }
    return bmp;
  }
}
"@
$p = Get-Process vmware | Where-Object { $_.MainWindowTitle -like "*BOB-ksi*" } | Select-Object -First 1
if (-not $p) { Write-Host "jendela BOB-ksi tidak ditemukan"; exit 1 }
$r = New-Object W+R
[void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
$w = $r.Rt - $r.L; $h = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$keluar = "captures\vm-konsol.png"
$bmp.Save($keluar)
Write-Host "tersimpan di $keluar (${w}x${h})"
