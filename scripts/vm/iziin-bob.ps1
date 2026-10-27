# Siapkan Windows supaya VM Bob bisa ikut demo: portproxy ke KDC di WSL + rule firewall.
# Jalankan sebagai ADMINISTRATOR (klik kanan PowerShell -> Run as administrator), satu kali saja.
#   powershell -ExecutionPolicy Bypass -File scripts\vm\iziin-bob.ps1

$ErrorActionPreference = "Stop"
$HostVmnet = "192.168.59.1"   # alamat adapter VMnet8 di laptop ini
$Akar = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

# 1. IP WSL (KDC) bisa berubah tiap boot. Pakai vm\ip-wsl.txt kalau masih segar,
#    kalau tidak ada baru tanya ke Ubuntu (wsl.exe di sesi admin kadang bermasalah).
$Akar = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$berkasIp = Join-Path $Akar "vm\ip-wsl.txt"
$WslIp = $null
if (Test-Path $berkasIp) {
  $WslIp = ((Get-Content $berkasIp) -split '\s+' | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
}
if (-not $WslIp) {
  $pathWsl = "/mnt/" + $berkasIp.Substring(0, 1).ToLower() + ($berkasIp.Substring(2) -replace '\\', '/')
  wsl.exe -d Ubuntu -e bash -lc "hostname -I > $pathWsl" 2>$null | Out-Null
  if (Test-Path $berkasIp) {
    $WslIp = ((Get-Content $berkasIp) -split '\s+' | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
  }
}
if (-not $WslIp) { Write-Host "GAGAL membaca IP WSL. Jalankan: wsl -d Ubuntu hostname -I" -ForegroundColor Red; exit 1 }
Write-Host "IP KDC (WSL Ubuntu)   = $WslIp"
Write-Host "IP Alice (VMnet8 host)= $HostVmnet  (Bob connect ke sini)"

# 2. Portproxy: 192.168.59.1:4444 -> WSL:4444 (VM tidak bisa menjangkau WSL langsung).
netsh interface portproxy delete v4tov4 listenaddress=$HostVmnet listenport=4444 2>$null | Out-Null
netsh interface portproxy add v4tov4 listenaddress=$HostVmnet listenport=4444 connectaddress=$WslIp connectport=4444
Write-Host "portproxy $HostVmnet`:4444 -> ${WslIp}:4444 OK"

# 3. Firewall: izinkan inbound dari VM (port KDC, chat Alice, dan server file proyek).
foreach ($p in @(4444, 5555, 8000)) {
  netsh advfirewall firewall delete rule name="ksi-port-$p" 2>$null | Out-Null
  netsh advfirewall firewall add rule name="ksi-port-$p" dir=in action=allow protocol=TCP localport=$p | Out-Null
  Write-Host "firewall TCP $p diizinkan"
}

Write-Host ""
Write-Host "Cek: netsh interface portproxy show all"
Write-Host "Habis demo, bersihin: netsh interface portproxy delete v4tov4 listenaddress=$HostVmnet listenport=4444"
