#!/bin/sh
# mulai-bob-lokal.sh -- dijalankan DI DALAM VM Alpine (Bob).
# Semua diambil dari LAPTOP (192.168.59.1:8000). VM tidak butuh internet, tidak pakai apk.
#   wget -q -O /root/b.sh http://192.168.59.1:8000/mulai-bob-lokal.sh && sh /root/b.sh

HOST=192.168.59.1
URL="http://$HOST:8000"

ip link set eth0 up 2>/dev/null
ip -4 -o addr show dev eth0 | grep -q inet || {
  echo "eth0 belum ada IP -> pasang 192.168.59.10/24"
  ip addr add 192.168.59.10/24 dev eth0
}
IP=$(ip -4 -o addr show dev eth0 | awk '{print $4}' | cut -d/ -f1 | head -1)
[ -n "$IP" ] || { echo "GAGAL: eth0 belum punya IP. Ketik: ip link set eth0 up; ip addr add 192.168.59.10/24 dev eth0"; exit 1; }
echo "== Bob VM == IP=$IP  laptop=$HOST"

# Tes pakai HTTP sungguhan, bukan ping: Windows (profil Public) memblokir ICMP masuk.
wget -q -O /dev/null "$URL/proyek.zip" || {
  echo "GAGAL: VM tidak bisa menjangkau $URL"
  echo "  cek: ifconfig  (harus ada inet addr 192.168.59.x)"
  echo "  cek: server file laptop masih terbuka? (python scripts\\vm\\kemas-dan-serve.py)"
  echo "  cek: VMware > VM > Settings > Network Adapter > NAT (VMnet8) + tercentang Connected"
  exit 1
}
echo "== 1/3 laptop terjangkau lewat HTTP =="

echo "== 2/3 pasang python3 (17 paket sudah kubungkus jadi satu tarball) =="
wget -q -O /tmp/py3.tgz "$URL/alpine-python3.tgz" || { echo "GAGAL unduh tarball"; exit 1; }
tar -xzf /tmp/py3.tgz -C / || { echo "GAGAL ekstrak"; exit 1; }
ldconfig 2>/dev/null
python3 -V || { echo "GAGAL: python3 tidak terpakai"; exit 1; }

echo "== 3/3 ambil proyek lalu jalankan BOB =="
wget -q -O /root/proyek.zip "$URL/proyek.zip" || { echo "GAGAL unduh proyek.zip"; exit 1; }
rm -rf /root/proyek
mkdir -p /root/proyek
python3 -c "import zipfile;zipfile.ZipFile('/root/proyek.zip').extractall('/root/proyek')"
cd /root/proyek
exec python3 -m src.main --role bob --kdc "$HOST:4444" --advertise-ip "$IP"
