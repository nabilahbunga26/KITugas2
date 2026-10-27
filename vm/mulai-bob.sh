#!/bin/sh
# mulai-bob.sh -- diunduh & dijalankan DI DALAM VM Alpine (Bob).
# Diambil dari host Windows: http://192.168.59.1:8000/mulai-bob.sh
# Asumsi: eth0 sudah punya IP (lihat baris paste di docs/09).

HOST=192.168.59.1
ip link set eth0 up 2>/dev/null
if ! ip -4 -o addr show dev eth0 | grep -q inet; then
  echo "eth0 belum ada IP -> pasang statis 192.168.59.10"
  ip addr add 192.168.59.10/24 dev eth0
  ip route replace default via 192.168.59.2
fi
# DNS VMware NAT = 192.168.59.2 (punya host). 8.8.8.8 sering dipotong jaringan kampus,
# jadi tulis ulang resolv.conf setiap kali (bukan cuma kalau kosong).
printf 'nameserver 192.168.59.2\nnameserver 8.8.8.8\n' > /etc/resolv.conf
IP=$(ip -4 -o addr show dev eth0 | awk '{print $4}' | cut -d/ -f1 | head -1)
if [ -z "$IP" ]; then
  echo "eth0 belum punya IP. Tempel dulu blok 'ip addr add ...' di docs/09."
  exit 1
fi
echo "== Bob VM == IP=$IP  host=$HOST"
ip route show default | grep -q 192.168.59.2 || ip route replace default via 192.168.59.2
ping -c 2 -W 3 192.168.59.2 >/dev/null 2>&1 || echo "   PERINGATAN: gateway NAT 192.168.59.2 tidak menjawab"

echo "== 1/3 pasang python3 =="
# Di ISO live, /etc/apk/repositories isinya baris yang DIKOMENTARI semua -> apk "unable to
# select package". Jadi tulis repo main secara eksplisit (tanpa tanda #) + refresh indeks.
echo "http://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64" > /etc/apk/repositories
apk update || echo "   (apk update gagal -- lanjut coba langsung)"
apk add --no-cache python3 || { echo "GAGAL apk. Jalankan 2 cek ini lalu kirim hasilnya:"; echo "   ping -c 2 192.168.59.2"; echo "   nslookup dl-cdn.alpinelinux.org"; exit 1; }

echo "== 2/3 ambil proyek dari laptop =="
wget -q -O /root/proyek.zip "http://$HOST:8000/proyek.zip" || { echo "GAGAL wget -- server laptop belum jalan?"; exit 1; }
mkdir -p /root/proyek
python3 -c "import zipfile;zipfile.ZipFile('/root/proyek.zip').extractall('/root/proyek')"
cd /root/proyek

echo "== 3/3 jalankan BOB (KDC via portproxy $HOST:4444, alamat terdaftar $IP) =="
exec python3 -m src.main --role bob --kdc "$HOST:4444" --advertise-ip "$IP"
