#!/bin/sh
# Bob TANPA internet VM: python3 diambil dari ISO Alpine "extended" yang ke-mount di /media/cdrom.
# Yang tetap dibutuhkan cuma jalur VM <-> laptop (192.168.59.1) -- itu jalan, bukti: wget b.sh sukses.

ip link set eth0 up 2>/dev/null
ip -4 -o addr show dev eth0 | grep -q inet || {
  ip addr add 192.168.59.10/24 dev eth0
  ip route replace default via 192.168.59.2
}
IP=$(ip -4 -o addr show dev eth0 | awk '{print $4}' | cut -d/ -f1 | head -1)
echo "== Bob VM (offline) == IP=$IP"

mount -o ro /dev/sr0 /media/cdrom 2>/dev/null
if [ ! -d /media/cdrom/main ]; then
  echo "GAGAL: /media/cdrom/main tidak ada."
  echo "  -> ISO yang terpasang di VM harus alpine-extended, bukan alpine-virt."
  echo "  -> cek: ls /media/cdrom"
  exit 1
fi

printf 'file:///media/cdrom/main\nfile:///media/cdrom/community\n' > /etc/apk/repositories
apk add --no-cache --allow-untrusted python3 || { echo "GAGAL apk dari CD"; exit 1; }

wget -q -O /root/proyek.zip http://192.168.59.1:8000/proyek.zip || { echo "GAGAL ambil proyek dari laptop"; exit 1; }
mkdir -p /root/proyek
python3 -c "import zipfile;zipfile.ZipFile('/root/proyek.zip').extractall('/root/proyek')"
cd /root/proyek
echo "== jalankan BOB (KDC via portproxy 192.168.59.1:4444, alamat terdaftar $IP) =="
exec python3 -m src.main --role bob --kdc 192.168.59.1:4444 --advertise-ip "$IP"
