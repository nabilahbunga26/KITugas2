# DISTRIBUSI SESSION KEY MENGGUNAKAN KDC
# DENGAN KOMUNIKASI AES-128 IMPLEMENTASI MANUAL

**Tugas Keamanan Informasi** — Key Distribution Center (KDC), Alice, dan Bob pada tiga IP address berbeda,
dilanjutkan komunikasi dua arah terenkripsi AES yang seluruh rondenya ditulis sendiri (tanpa library crypto).

| Anggota | NRP |
|---|---|
| Nabilah Bunga Sulistia | 5025241073 |
| Callista Fidelya Robal Gultom | 5025241086 |

Tanggal pengerjaan: 27 Oktober 2026 · Bahasa: Python 3.12 (Windows) / 3.14 (WSL) / 3.12 (VM Alpine) · **Tanpa dependency eksternal**

---

## DAFTAR ISI

1. [Ringkasan](#1-ringkasan)
2. [Pemenuhan ketentuan tugas](#2-pemenuhan-ketentuan-tugas)
3. [Landasan teori](#3-landasan-teori)
4. [Perancangan sistem](#4-perancangan-sistem)
5. [Implementasi (peta kode)](#5-implementasi-peta-kode)
6. [Cara menjalankan](#6-cara-menjalankan)
7. [Demo: urutan mengetik di 3 terminal](#7-demo-urutan-mengetik-di-3-terminal)
8. [Pengamatan dengan Wireshark](#8-pengamatan-dengan-wireshark)
9. [Hasil dan validasi](#9-hasil-dan-validasi)
10. [Pembagian tugas tim](#10-pembagian-tugas-tim)
11. [Fitur tambahan](#11-fitur-tambahan)
12. [Antisipasi pertanyaan dosen](#12-antisipasi-pertanyaan-dosen)
13. [Troubleshooting nyata yang kami temui](#13-troubleshooting-nyata-yang-kami-temui)
14. [Keterbatasan dan kesimpulan](#14-keterbatasan-dan-kesimpulan)
15. [Referensi dan pernyataan orisinalitas](#15-referensi-dan-pernyataan-orisinalitas)
16. [Lampiran](#16-lampiran)

---

## 1. RINGKASAN

Tiga proses berjalan di **tiga mesin berbeda dengan tiga IP berbeda** di satu laptop:

```
            KDC  172.20.93.6:4444            (WSL2 Ubuntu  — pihak tepercaya)
            /                        \
     REG + REQ1/REP2 (K_as)      REG (K_bs)
          /                            \
  ALICE 192.168.59.1:5555  <----->  BOB 192.168.59.131:5555
  (Windows host / VMnet8)   chat     (VMware VM Alpine 3.20, jalan di RAM)
                          AES manual
```

* KDC membangkitkan **session key `K_ab`** (ASCII 16 karakter) dan mengirimkannya **terbungkus dua lapis**:
  `{K_ab, B, {K_ab, A}_K_bs}_K_as`.
* Setelah langkah 5, Alice dan Bob memegang `K_ab` yang sama; **KDC tidak dilibatkan lagi** dalam chat.
* Semua payload di kabel berupa **heks ciphertext**; key dan plaintext selalu **ASCII**.
* Key bisa diganti **tanpa restart** lewat menu interaktif, dan kedua sisi saling mengonfirmasi key baru
  dengan sidik (key confirmation).
* AES-128/192/256 ditulis manual — S-Box pun **dibangkitkan** dari aritmetika GF(2⁸), bukan tabel tempel —
  dan dibuktikan cocok dengan **vektor known-answer FIPS-197 Lampiran C**.

Peran KDC bukan sebagai perantara pesan: dia hanya menjawab `REG` (mencatat nama → IP:port) dan `REQ1`
(menerbitkan kunci). `TICKET3`, `CHAL4`, `RESP5`, dan `MSG` mengalir langsung antara Alice dan Bob.

---

## 2. PEMENUHAN KETENTUAN TUGAS

| No | Ketentuan | Di mana dipenuhi | Bukti saat demo | Status |
|----|-----------|-----------------|-----------------|--------|
| 2 | Distribusi key KDC–Alice–Bob pada **3 IP berbeda**, skenario sesuai PPT, setelah langkah 5 komunikasi AES | §3–§4; `src/ksilib/kdc/`; topologi §1 | log `[LANGKAH 1]`…`[LANGKAH 5]` + `ip.addr` berbeda di Wireshark | **SELESAI** |
| 3 | Komunikasi dua arah, dua-duanya bisa jadi pengirim & penerima | arsitektur *client–client*: kedua node membuka listener dan koneksi keluar (`net/link.py: Listener` + `one_shot`) | `k halo dari alice` → muncul di Bob; `k halo balik` → muncul di Alice | **SELESAI** |
| 4 | Key & plaintext **ASCII**, ciphertext **HEX**; AES & KDC **manual**; key tidak di-hardcode | `src/ksilib/aes/` (manual), `utils/config.py` (key dari `.env`/input), `to_ascii()` menolak non-ASCII | `grep -RinE "import (Crypto\|cryptography)" src/` kosong; ciphertext heks di log & Wireshark | **SELESAI** |
| 5 | Interaktif, key diganti tanpa restart | menu `d k r g u s q` di `src/main.py:interaktif()` | `g` + key baru di dua sisi → `auth=True`, ciphertext berubah, program tidak restart | **SELESAI** |
| 6 | Wireshark siap: interface benar, filter disiapkan, transmisi terlihat | §8 | `captures/demo.pcapng` + filter `tcp contains "REP2"`; filter `tcp contains "halo"` = 0 paket | **SELESAI** |
| 7 | Program jalan; tiap anggota paham, tidak baca plek ketiplek | §12 Q&A; not poin di §7 | sesi saling-tanya antaranggota sebelum tampil | **SELESAI (latihan tetap wajib)** |
| 11 | Anti-plagiarisme | §15; komentar kode merujuk pasal FIPS-197, bukan menyalin kode orang lain | mampu menjelaskan asal-usul tiap fungsi baris per baris | **SELESAI** |
| 12 | Fitur tambahan bernilai tambah | §11: key confirmation (sidik), TTL session key, auto-detect IP, `--advertise-ip`, known-answer FIPS-197, mode AES 128/192/256 | demo fitur + penjelasan trade-off | **SELESAI** |

> Butir soal no. 1, 8, 9, 10 (biasanya administrasi: format laporan, tenggat, cara pengumpulan) belum
> kami terima, jadi tidak dipetakan di tabel ini.

---

## 3. LANDASAN TEORI

### 3.1 Key Distribution Center

Masalahnya: Alice dan Bob tidak pernah bertemu sebelumnya dan tidak punya kunci bersama. Kalau setiap
pasangan pengguna harus punya kunci sendiri, jumlah kunci tumbuh kuadratik (N²) dan setiap orang harus
menyimpan semuanya. KDC menyelesaikan ini: **tiap pengguna hanya menyimpan satu master key ke KDC**
(`K_as` untuk Alice, `K_bs` untuk Bob), dan KDC yang membekalkan kunci sesi sementara `K_ab` setiap kali
sesi baru dibutuhkan.

Skenario yang kami ikuti adalah Needham–Schroeder symmetric:

| # | Pengirim → Penerima | Pesan | Penjelasan |
|---|---------------------|-------|------------|
| 1 | Alice → KDC | `A, B` | minta izin komunikasi dengan Bob |
| 2 | KDC → Alice | `{K_ab, B, {K_ab, A}_K_bs}_K_as` | KDC bangkitkan `K_ab`; bagian dalam adalah **tiket** yang hanya bisa dibuka Bob |
| 3 | Alice → Bob | `{K_ab, A}_K_bs` | Alice **meneruskan** tiket — dia sendiri tidak bisa membacanya |
| 4 | Bob → Alice | `{N_b}_K_ab` | Bob membuktikan ia baru bisa membaca tiket: tantangan nonce |
| 5 | Alice → Bob | `{N_b + 1}_K_ab` | Alice membuktikan ia pemegang `K_ab` yang sah → **kunci sama di dua sisi** |
| 6 | Alice ↔ Bob | chat AES dengan `K_ab` | KDC sudah tidak dipakai |

Dua serangan yang digagalkan langkah 4–5:
* **Replay tiket lama** — tiket direkam penyadap dan dikirim ulang; tanpa nonce, Bob akan mengira itu sesi baru.
  Challenge–response memaksa bukti bahwa lawan bicara memegang `K_ab` **saat itu juga**.
* **Alice menyamar jadi Bob** — mustahil, karena tiket dienkripsi `K_bs` yang hanya diketahui Bob dan KDC.

Catatan jujur (wajib disebut kalau ditanya): versi buku memakai `f(N_a)` dan tantangan dua arah. Kami
menyederhanakan menjadi satu tantangan dengan balasan `N_b + 1` dan memindahkan `N_a` ke dalam payload
`NONCE=...|REPLY=...`. Ini **deviasi** dari textbook, bukan kesalahan, dan tercatat di §5.4.

### 3.2 AES yang ditulis manual

AES = blok cipher 128-bit: data dipotong blok 16 byte, tiap blok diproses beberapa ronde
(AES-128: 10, AES-192: 12, AES-256: 14 ronde; jumlah round key = ronde + 1).

| Transformasi | Apa yang terjadi | Kenapa ada |
|---|---|---|
| **SubBytes** | tiap byte diganti lewat S-Box | *confusion* — hubungan key↔ciphertext jadi nonlinear |
| **ShiftRows** | baris ke-i digeser kiri i posisi | menyebarkan byte antar kolom |
| **MixColumns** | tiap kolom dikalikan matriks di GF(2⁸) | *diffusion* lintas baris |
| **AddRoundKey** | XOR state dengan round key ke-i | mengikat kunci ke data |

Urutan: `AddRoundKey(0)` → (Nr−1)× [`SubBytes` → `ShiftRows` → `MixColumns` → `AddRoundKey`] →
ronde terakhir **tanpa `MixColumns`**. Alasannya (FIPS-197 §5.3): supaya struktur enkripsi dan dekripsi
saling invers dengan kunci yang sama; kalau ronde terakhir tetap dicampur, `InvMixColumns` di awal
dekripsi tidak akan menghapusnya.

**State disimpan kolom-demi-kolom (column-major)** — ini sumber bug paling sering saat menulis manual.

**Key expansion**: dari key 16 byte dibuat 4 word awal, lalu `w[i] = w[i-4] ⊕ T(w[i-1])`, dengan
`T = RotWord ∘ SubWord  Rcon` dan Rcon hanya dipakai saat `i % 4 == 0`. Untuk AES-128 dihasilkan 44 word = 11 round key.

**S-Box dibangkitkan, bukan disalin.** Kami menghitung invers tiap byte di GF(2⁸) (modulus polynomial
`0x11B`), lalu transformasi affine (rotasi 1, 2, 3, 4 bit dan XOR), lalu XOR `0x63`. Karena itu
`test_sbox_dibangkitkan_benar()` membuktikan `sbox[0x00]=0x63` dan `sbox[0x53]=0xED` cocok dengan tabel resmi.

**Encoding & padding.** Key dan plaintext **ASCII** (byte 0–127; di luar itu ditolak dengan pesan jelas,
bukan diam-diam salah hitung blok). Ciphertext **heks huruf kecil**. Padding **PKCS#7**: nilai tiap byte
padding = jumlah byte padding; kalau input sudah pas 16 byte ditambahkan satu blok penuh `0x10`.
Mode yang dipakai **ECB** — dipilih karena tidak perlu IV sehingga kanal teks tetap sederhana dan mudah
ditunjuk di Wireshark; kelemahannya (dua blok identik → ciphertext identik) kami jelaskan di §14.

---

## 4. PERANCANGAN SISTEM

### 4.1 Tabel alamat final

| Entitas | Mesin nyata | IP | Port | Master key (ASCII 16) |
|---|---|---|---|---|
| **KDC** | WSL2 Ubuntu di laptop | `172.20.93.6` | 4444 | menyimpan `K_as` **dan** `K_bs` |
| **Alice** | Windows host, adapter VMware VMnet8 | `192.168.59.1` | 5555 | `KasMasterKeyAAAA` |
| **Bob** | VMware VM "BOB-ksi", Alpine 3.20 live dari ISO (di RAM) | `192.168.59.131` (DHCP VMnet8; bisa juga statis `.10`) | 5555 | `KbsMasterKeyBBBB` |

Tiga IP, tiga mesin, tiga sistem operasi. **Bukan** tiga port di satu IP.

### 4.2 Kenapa perlu `ADVERTISE_IP`

WSL2 dan VMware sama-sama memakai NAT, dan keduanya adalah **pulau terpisah**: VM tidak bisa menjangkau
`172.20.x` milik WSL, dan sebaliknya. Akibatnya:

1. KDC tetap di WSL, tapi **hanya menerima** koneksi masuk. VM Bob menghubungi KDC lewat
   **portproxy** Windows `192.168.59.1:4444 → 172.20.93.6:4444` (dibuat `scripts/vm/iziin-bob.ps1`, butuh admin).
2. Alamat yang dilihat KDC di header paket adalah alamat **host** (`172.20.80.1` / `192.168.59.1`), bukan
   alamat VM — kalau itu yang dipakai, Alice tidak akan pernah bisa membalas ke Bob.
3. Karena itu tiap node **mengumumkan sendiri** IP yang bisa diroute pasangannya:
   `REG|NAMA|PORT|<advertise-ip>`. Alice mengumumkan `192.168.59.1`, Bob mengumumkan IP VM-nya.

Ini juga yang membuat tidak ada satu pun IP yang perlu diketik manual saat demo, selain IP KDC di config.

### 4.3 Keputusan desain

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Transport | **TCP** | urutan pesan jelas, mudah diamati di Wireshark, tidak perlu fragmentasi sendiri |
| Bentuk pesan di kabel | **satu baris ASCII, field dipisah `|`, ciphertext heks** | terbaca manusia saat demo; framing pakai `readline` (`\n`) |
| Master key | ASCII 16 char dari `config/hosts/*.env` | tidak di-hardcode (ketentuan 4) |
| Session key | dibangkitkan KDC, ASCII 16 char (`secrets`) | hasil distribusi; panjang menentukan 128/192/256 |
| Mode | **ECB + PKCS#7** | tanpa IV, paling gampang dijelaskan; kelemahan pola diakui di §14 |
| Bentuk program | REPL menu interaktif | ketentuan 5 |
| Topologi | client–client (dua-duanya listener + connector) | ketentuan 3 |

### 4.4 Format pesan yang benar-benar dikirim

| Langkah | Pesan di kabel | Isi sebelum dienkripsi | Key |
|---|---|---|---|
| registrasi | `REG\|BOB\|5555\|192.168.59.131` → `REGOK\|BOB` | — (terbuka: nama, port, alamat) | — |
| 1 | `REQ1\|ALICE\|BOB` | — | — |
| 2 | `REP2\|<heks>` | `K=<K_ab>\|B=<ip:port>\|TICKET=<heks>` | `K_as` |
| 3 | `TICKET3\|<heks>` | `K=<K_ab>\|NAME=ALICE\|A=<ip:port>` | `K_bs` |
| 4 | `CHAL4\|<nonce>\|<heks>` | `NONCE=<n>` | `K_ab` |
| 5 | `RESP5\|<heks>` | `NONCE=<n>\|REPLY=<n+1>` | `K_ab` |
| 6 | `MSG\|<heks>` | plaintext chat ASCII | `K_ab` |
| kontrol | `KCONF\|<sidik4hex>` → `KCONF\|OK`/`BEDA` | pencocokan key pasca-rotasi | — |
| bantu | `PING\|KDC` → `PONG\|KDC\|<jumlah node>` | uji konektivitas | — |

---

## 5. IMPLEMENTASI (PETA KODE)

### 5.1 Struktur

```
tugas-keamanan-informasi/
├── README.md                  <- dokumen ini (satu-satunya dokumen)
├── src/
│   ├── main.py                entry point semua peran: --role kdc|alice|bob [--kdc IP:PORT] [--advertise-ip IP]
│   ├── kdc/main.py            menjalankan listener KDC
│   ├── alice/main.py          alias peran ALICE
│   ├── bob/main.py            alias peran BOB
│   └── ksilib/
│       ├── aes/sbox.py        gmul, invers GF(2^8), S-Box & inverse S-Box DIBANGKITKAN
│       ├── aes/core.py        expand_key, encrypt_block, decrypt_block, pad/unpad, encrypt_hex, decrypt_hex, to_ascii
│       ├── kdc/protocol.py    build/parse pesan, sidik(), bangkitkan_session_key(), nonce(), inner/outer
│       ├── kdc/server.py      logika KDC: registrasi, REQ1→REP2, TTL, daftar nama→alamat
│       ├── kdc/node.py        Node Alice/Bob: registrasi, alur langkah 1–5, chat, ganti key, status
│       ├── net/link.py        send_line/read_line, connect, one_shot, Listener(thread), ip_yang_dipakai_untuk
│       ├── utils/config.py    pembaca config/hosts/<peran>.env (Kunci=nilai, komentar #)
│       └── utils/log.py       log ber-stamp [jam][PERAN], menulis ke captures/<peran>.log
├── config/hosts/              kdc.env · alice.env · bob.env (+ .example)
├── tests/
│   ├── aes/test_fips197.py    known-answer FIPS-197 C.2/C.3/C.4 + S-Box + Rcon + GF(2^8) + jumlah round key
│   └── test_loopback_e2e.py   3 proses di 127.0.0.1: langkah 1–5 + chat dua arah + rotasi key
├── scripts/
│   ├── demo/rehearse.py       gladi 1 laptop (semua otomatis, alamat 127.0.0.1) — BUKAN topologi dinilai
│   ├── probe/listen.py        uji TCP antar perangkat
│   ├── probe/send.py          pasangan probe di atas
│   └── vm/                    iziin-bob.ps1 · kemas-dan-serve.py · mirror-apk.py · rakit-python3.py · tangkap-vm.ps1
├── vm/                        VM Bob: bob-vm.vmx, alpine-virt.iso, mulai-bob-lokal.sh, proyek.zip, alpine-python3.tgz
├── captures/                  *.log hasil demo + demo.pcapng (Wireshark)
├── report/bab-4-hasil/        salinan log KDC/Alice/Bob/gladi sebagai bukti
└── references/                PPT kelas + FIPS-197 (ISI SENDIRI SEBELUM DIKUMPULKAN)
```

### 5.2 AES manual — `src/ksilib/aes/`

| Fungsi | Peran |
|---|---|
| `gmul(a,b)` | perkalian di GF(2⁸) dengan reduce `0x11B` — dipakai S-Box dan MixColumns |
| `_build()` | S-Box: invers GF(2⁸) → transformasi affine → XOR `0x63`; mengembalikan tabel + inverse-nya |
| `expand_key(key)` | key ASCII 16/24/32 byte → round key (44/52/60 word) |
| `_sub_bytes` / `_shift_rows` / `_mix_columns` / `_add_round_key` | 4 transformasi, parameter `inverse=True` untuk dekripsi |
| `encrypt_block` / `decrypt_block` | susunan ronde sesuai FIPS-197 (round terakhir tanpa MixColumns) |
| `pad` / `unpad` | PKCS#7 blok 16 |
| `encrypt_hex(key_ascii, teks_ascii) -> heks` | pintu masuk protocol; selalu ASCII masuk, heks keluar |
| `decrypt_hex(heks, key_ascii) -> ASCII` | kebalikannya; heks cacat → `ValueError`, bukan crash |
| `to_ascii(text)` | validasi: karakter di luar 0–127 ditolak dengan pesan jelas |

### 5.3 KDC & node — `src/ksilib/kdc/`

* `server.py` — menyimpan peta nama→`(ip, port, chat_port)` dari `REG`, membangkitkan `K_ab`
  (`bangkitkan_session_key()`, `secrets.choice` atas alphabet ASCII), menyusun REP2 berlapis, dan
  (fitur tambahan) memakai ulang `K_ab` selama TTL belum lewat.
* `node.py` — `registrasi()`, `mulai_sebagai_pengaju()` (langkah 1→2→3→tunggu CHAL→kirim RESP5),
  `mulai_sebagai_penerima()` (tunggu TICKET→kirim CHAL4→tunggu RESP5), `kirim()`, `ganti_key()`, `status()`.
  Batas tunggu 300 detik per langkah supaya tidak gagal saat demo live.
* `protocol.py` — `build/parse` baris `|`, `inner/outer` untuk payload `K=..|A=..` di dalam ciphertext,
  `sidik()` = checksum 32-bit untuk key confirmation, `nonce()`.

### 5.4 Deviasi dari textbook (sengaja, catat di laporan)

1. Tiket ikut membawa alamat pengaju (`A=<ip:port>`) supaya Bob bisa membalas tanpa konfigurasi IP.
2. KDC mengambil alamat dari pendaftaran `REG` (header TCP + `ADVERTISE_IP`), bukan dari buku alamat terpisah.
3. Balasan tantangan memakai `REPLY = nonce + 1` (versi sederhana dari `f(N_a)`), tantangan satu arah.
4. `sidik(key)` = checksum 32-bit untuk mencocokkan key, **bukan** hash kriptografis.
5. Framing memakai baris teks ASCII berakhiran `\n`, bukan header panjang 2 byte seperti rancangan awal.

---

## 6. CARA MENJALANKAN

### 6.1 Persiapan sekali saja (butuh ADMIN)

```powershell
cd C:\Users\LENOVO\Documents\Qoder\2026-10-27\0aff9277\tugas-keamanan-informasi
powershell -ExecutionPolicy Bypass -File scripts\vm\iziin-bob.ps1
```

Isinya: portproxy `192.168.59.1:4444 → <IP WSL>:4444` + rule firewall inbound TCP **4444, 5555, 8000**.
**Ulangi hanya kalau IP WSL berubah** (cek `wsl -d Ubuntu hostname -I`; IP WSL berubah tiap boot).

### 6.2 Empat jendela

| # | Jendela | Folder kerja | Perintah |
|---|---|---|---|
| 0 | PowerShell (server file VM) | folder proyek | `python scripts\vm\kemas-dan-serve.py` |
| 1 | **WSL Ubuntu** — KDC | `/mnt/c/Users/LENOVO/Documents/Qoder/2026-10-27/0aff9277/tugas-keamanan-informasi` | `python3 -m src.main --role kdc` |
| 2 | **PowerShell** — Alice | `C:\Users\LENOVO\Documents\Qoder\2026-10-27\0aff9277\tugas-keamanan-informasi` | `python -m src.main --role alice` |
| 3 | **VMware VM "BOB-ksi"** — Bob | di dalam VM, lihat §6.3 | otomatis lewat skrip |

Jalankan **KDC paling dulu**. Kalau Bob belum ada (gladi di satu laptop), pakai `--port 5556` supaya
tidak rebutan port dengan Alice.

### 6.3 Menghidupkan Bob di VM Alpine

VM `vm/bob-vm.vmx` boot Alpine 3.20 **live dari ISO** (tanpa install, jalan di RAM). Login: user `root`,
tanpa password. Lalu tempel dua blok ini di konsol VM:

```sh
ip link set eth0 up; ip addr add 192.168.59.10/24 dev eth0
```
```sh
wget -q -O /root/b.sh http://192.168.59.1:8000/mulai-bob-lokal.sh && sh /root/b.sh
```

Skrip itu: memasang IP → **tes HTTP sungguhan** ke laptop → membongkar `alpine-python3.tgz`
(17 paket python3 + seluruh `.so` yang dibutuhkannya, sudah disiapkan `scripts/vm/mirror-apk.py` dan
`scripts/vm/rakit-python3.py`) → mengunduh `proyek.zip` → menjalankan
`python3 -m src.main --role bob --kdc 192.168.59.1:4444 --advertise-ip <ip-nya-sendiri>`.

Karena VM **tidak punya internet** di jaringan kampus ini, semua berkas diambil dari laptop
(satu subnet VMnet8). `vm/mulai-bob.sh` adalah rute lama lewat internet, disimpan sebagai cadangan.

> Alpine live = jalan di RAM. **VM di-restart → `/root` hilang**, tinggal tempel ulang dua blok di atas.

### 6.4 Gladi cepat satu laptop (bukan topologi dinilai)

```powershell
python scripts\demo\rehearse.py
```

Menjalankan KDC+Alice+Bob dan mengetikkan langkahnya otomatis di `127.0.0.1`, lalu mencetak log-nya.
Pakai ini untuk memastikan protokol sehat sebelum menyentuh VM.

---

## 7. DEMO: URUTAN MENGETIK DI 3 TERMINAL

**Mulai Wireshark dulu** (§8), baru ketik apa pun.

| # | Jendela | Ketik | Yang harus muncul |
|---|---|---|---|
| 1 | **Bob** | `d` | `[TUNGGU] menunggu tiket dari pasangan di port 5555 ...` (dan di KDC: `[REG] BOB terdaftar di 192.168.59.131:5555`) |
| 2 | **Alice** | `d` | `[LANGKAH 1]` → `[LANGKAH 2]` (heks) → `[LANGKAH 3] ... OK-TICKET` → `[LANGKAH 4]` → `[LANGKAH 5]` → `SIAP` |
| 3 | **Alice** | `k halo dari alice` | di Bob: `TERIMA: halo dari alice` |
| 4 | **Bob** | `k halo balik dari bob` | di Alice: `TERIMA: halo balik dari bob` |
| 5 | **Bob** | `g` lalu `KunciGantiDemo26` | `[KEY] ... diganti` + pasangan bilang `KCONF|OK`, `auth=True` |
| 6 | **Alice** | `g` lalu `KunciGantiDemo26` | sama, tanpa restart program |
| 7 | **Alice** | `k pesan setelah ganti key` | muncul lagi di Bob dengan ciphertext berbeda |
| 8 | **Bob** lalu **Alice** | `s` | `ip_terdaftar` **beda**, `session_key` **sama**, `auth=True` |

**Aturan wajib:** `d` di **Bob lebih dulu** daripada `d` di Alice. Kalau terbalik, Alice menunggu tiket
yang tidak ada. Kalau muncul `ERR|BOB belum mendaftar ke KDC` → ketik `d` di Bob, lalu `d` lagi di Alice.

Perintah menu: `d` jalankan skenario · `k <teks>` kirim · `r` baca kotak masuk · `g` ganti key ·
`u` uji AES satu baris (masukkan key & plaintext, lihat heks-nya) · `s` status · `q` keluar.

---

## 8. PENGAMATAN DENGAN WIRESHARK

Wireshark 4.4.19 + Npcap terpasang di laptop ini. Interface yang dicentang (**Capture → Options**, `Ctrl+K`):

* `VMware Network Adapter VMnet8` → Alice ↔ Bob (chat AES, port 5555) dan Bob → portproxy KDC
* `vEthernet (WSL (Hyper-V firewall))` → Alice ↔ KDC (port 4444)

Mulai tangkapan **sebelum** menjalankan program, simpan ke `captures/demo.pcapng` (`Ctrl+S`).

| Tujuan | Filter |
|---|---|
| Trafik distribusi key | `tcp.port == 4444` |
| Trafik chat Alice ↔ Bob | `tcp.port == 5555` |
| Semua yang bersinggungan dengan Bob | `ip.addr == 192.168.59.131` |
| Tiket terenkripsi (langkah 2) | `tcp contains "REP2"` |
| Pesan chat | `tcp contains "MSG\|"` |
| Pendaftaran node | `tcp contains "REG\|BOB"` |
| Satu percakapan saja | `tcp.stream == N` (dari *Follow → TCP Stream*) |
| Buang ruido | `!(arp || dns || llmnr || nbss || mdns) && tcp.port == 4444` |

**Bukti yang ditunjuk ke dosen:** klik kanan paket `REP2` → *Follow → TCP Stream* → isinya
`REP2|5ae4b41cb512...` (heks panjang), tidak ada `K=` dan tidak ada nama session key.

**Bukti negatif (paling kuat), jalankan setelah demo:**

```
tcp contains "halo"
tcp contains "Sx82"
```

Keduanya harus **0 paket** → plaintext chat dan session key tidak pernah lewat jaringan dalam bentuk terbaca.

**Pembanding:** tanpa enkripsi, kolom Info/ASCII di stream akan menampilkan `halo dari alice` langsung.
Dengan program kami, yang sama menjadi `MSG|b4a2...` (heks).

---

## 9. HASIL DAN VALIDASI

### 9.1 Uji otomatis

```powershell
python -m pytest tests -q
```

6 tes: `test_sbox_dibangkitkan_benar`, `test_rcon`, `test_gf28`, `test_vektor_fips197` (AES-128/192/256
Lampiran C), `test_jumlah_round_key`, dan `test_langkah_1_5_dan_chat_dua_arah` (3 proses + chat dua arah
+ rotasi key). Vektornya:

| Standar | Key (heks) | Plaintext (heks) | Ciphertext (heks) |
|---|---|---|---|
| FIPS-197 C.2 (AES-128) | `000102030405060708090a0b0c0d0e0f` | `00112233445566778899aabbccddeeff` | `69c4e0d86a7b0430d8cdb78070b4c55a` |
| FIPS-197 C.3 (AES-192) | `000102...16171819` | sama | `dda97ca4864cdfe06eaf70a0ec0d7191` |
| FIPS-197 C.4 (AES-256) | `000102...1e1f` | sama | `8ea2b7ca516745bfeafc49904b496089` |

> Catatan: tes end-to-end memakai port **4444/5555/5556** di `127.0.0.1`. Kalau demo masih jalan, port itu
> terisi dan tes tersebut gagal — tutup dulu KDC/Alice/Bob, lalu jalankan ulang `pytest`.

### 9.2 Bukti manual

```powershell
Select-String -Path src\*.py -Pattern "Crypto|cryptography" -Recurse   # kosong = AES ditulis manual
```

Log nyata hasil menjalankan demo (salinan di `report/bab-4-hasil/`):

```
[20:35:50][KDC]   [REG] ALICE terdaftar di 192.168.59.1:5555 -- sumber alamat: diumumkan sendiri
[20:35:51][KDC]   [KDC] session key baru: 'Sx82l9g4WX3wxdLQ' (ASCII 16 char) -- hanya tampil di layar KDC
[20:35:51][KDC]   [KDC] plaintext tiket -> K=Sx82l9g4WX3wxdLQ|NAME=ALICE|A=192.168.59.1:5555
[20:35:51][ALICE] [LANGKAH 2] decrypt master key ALICE -> K=Sx82l9g4WX3wxdLQ|B=192.168.59.131:5555|TICKET=244246b6...
[20:35:51][ALICE] [LANGKAH 3] KIRIM tiket ke BOB 192.168.59.131:5555 -> OK-TICKET
```

`session_key` yang sama muncul di Alice dan Bob; di kabel hanya heks.

### 9.3 Tabel test case yang harus diisi saat demo live

| # | Plaintext (ASCII) | Key (ASCII) | Ciphertext (HEX) hasil program | Catatan |
|---|---|---|---|---|
| 1 | `hello` | 16 char | | satu blok + padding |
| 2 | `0123456789abcdef` | `0123456789abcdef` | | cocok vektor FIPS? |
| 3 | `a` | 16 char | | uji padding blok penuh |
| 4 | kalimat > 16 char | 16 char | | multi-blok ECB |
| 5 | `haloño` | 16 char | **ditolak** | validasi ASCII (ketentuan 4) |

---

## 10. PEMBAGIAN TUGAS TIM

Prinsip: tiap orang menulis modulnya sendiri, tapi **dua-duanya wajib bisa menjelaskan semuanya**
(ketentuan 7 — demo tanpa baca teks).

| Anggota | NRP | Modul yang ditulis | Bagian yang dijelaskan saat demo |
|---|---|---|---|
| **Nabilah Bunga Sulistia** | 5025241073 | `ksilib/aes/` (S-Box dibangkitkan, round, key expansion, padding), `tests/aes/`, `utils/config.py` | AES manual: 4 transformasi, urutan ronde, kenapa round terakhir tanpa MixColumns, bukti known-answer FIPS-197, ASCII↔heks |
| **Callista Fidelya Robal Gultom** | 5025241086 | `ksilib/kdc/` (protocol, server, node), `ksilib/net/link.py`, `src/main.py` (menu interaktif), topologi VM/WSL + skrip `scripts/vm/` | Arsitektur 3 IP, langkah 1–5 KDC, chat dua arah, ganti key tanpa restart, Wireshark & filter |

Checklist "selesai" per modul: ada minimal satu tes yang gagal kalau modul dirusak · komentar menjelaskan
"kenapa", bukan "apa" · sudah diuji lintas IP nyata (bukan localhost saja) · penanggung jawab bisa
menjelaskan tanpa membuka berkas.

---

## 11. FITUR TAMBAHAN

| Fitur | Masalah yang dipecahkan | Di mana | Trade-off |
|---|---|---|---|
| **Key confirmation (sidik key)** | Setelah `g`, kedua sisi bisa saja memegang key berbeda tanpa sadar | `protocol.sidik()` + pesan `KCONF`; `auth_ok` dipulihkan saat sidik cocok | sidik 32-bit bocor ke jaringan = bocor 4 bit-info kunci; cukup untuk demo, bukan untuk produksi |
| **TTL session key** | Tiket tak pernah kedaluwarsa → bisa dipakai ulang selamanya | `SESSION_KEY_TTL_SECONDS` di `kdc/server.py` (0 = mati) | butuh jam yang relatif sinkron antar mesin |
| **Auto-detect IP lokal** | User tidak perlu mengetik IP mesinnya | `link.ip_yang_dipakai_untuk()` (UDP connect trick) | hanya benar untuk rute ke KDC; karena itu tetap ada `--advertise-ip` |
| **`--advertise-ip`** | WSL/VMware dua pulau NAT: alamat di header paket bukan alamat yang bisa diroute | `main.py` → `Node.advertise_ip` → `REG` | memindahkan tanggung jawab kebenaran IP ke konfigurasi |
| **Known-answer FIPS-197** | Klaim "AES kami benar" tanpa bukti | `tests/aes/test_fips197.py` | tidak menguji seluruh kemungkinan, hanya vektor resmi |
| **AES-128/192/256** | Key user tidak selalu 16 char | `expand_key()` menerima 16/24/32 byte | panjang key harus divalidasi, bukan dipotong diam-diam |
| **Menu `u` uji AES seketika** | Dosen minta "coba enkripsikan kata ini sekarang" | `main.py:interaktif()` | — |
| **Log plaintext↔ciphertext berpasangan** | Pembuktian ketentuan 4 saat demo | `utils/log.py` → `captures/<peran>.log` | log berisi key = risiko; jangan disebar |

---

## 12. ANTISIPASI PERTANYAAN DOSEN

| Ditanya | Jawab inti |
|---|---|
| Kenapa butuh KDC? | Dua pihak tidak punya kunci bersama; tanpa KDC butuh N² kunci. Tiap orang cukup satu master key ke pihak tepercaya. |
| Di mana session key dibuat? | Di **KDC** (`bangkitkan_session_key()`), ASCII 16 char, tidak pernah dikirim terbuka — dibungkus `{K_ab,B,{K_ab,A}_K_bs}_K_as`. |
| Kenapa Alice tidak bisa baca tiket Bob? | Tiket dienkripsi `K_bs`. Alice cuma meneruskan (langkah 3). |
| Jadi KDC ikut mengirim pesan chat? | Tidak. KDC hanya menjawab `REG` dan `REQ1`. `TICKET3/CHAL4/RESP5/MSG` langsung antar node; matikan KDC setelah `SIAP`, chat tetap jalan. |
| Kenapa langkah 4–5 perlu? | Mencegah replay tiket lama: memaksa bukti kedua pihak memegang `K_ab` **sekarang**, bukan kemarin. |
| Kenapa round terakhir tanpa MixColumns? | Supaya enkripsi/dekripsi saling invers dengan kunci sama (FIPS-197 §5.3). |
| State AES disimpan bagaimana? | Column-major, 4 baris × Nb kolom. |
| Kenapa ECB? | Tanpa IV, kanal teks tetap satu baris heks dan mudah ditunjuk di Wireshark. Kelemahannya: blok identik → ciphertext identik (pola tidak hilang). |
| Kenapa heks, bukan biner? | Ciphertext biner tidak aman lewat kanal teks ASCII; heks tetap terbaca manusia saat demo. |
| Key di-hardcode? | Tidak. `config/hosts/*.env` dibaca `utils/config.py`, dan bisa diganti runtime lewat `g`. `Select-String` di `src/` membuktikan tidak ada literal key. |
| Bedanya dengan library? | S-Box kami **bangkitkan** dari invers GF(2⁸) + affine; round, key expansion, padding ditulis sendiri. Buktinya vektor FIPS-197 cocok. |
| Kalau `K_as` bocor? | Penyadap bisa membuka semua REP2 Alice → semua `K_ab` terbuka. Karena itu sistem nyata pindah ke asimetrik/DH; dan itu keterbatasan model KDC. |
| Single point of failure? | Ya: KDC. Kalau mati, sesi **baru** tidak bisa dibuat; sesi yang sudah `SIAP` tetap jalan karena `K_ab` sudah di tangan kedua node. |
| Bisa kena man-in-the-middle? | Penyadap bisa merekam tiket dan ciphertext, tapi tanpa `K_bs`/`K_as` tidak memperoleh `K_ab`. Yang belum kami tangani: **integritas** (tidak ada MAC), jadi pesan bisa diacak/ditolak — bukan dibaca. |
| Kenapa IP Bob `192.168.59.x` padahal KDC `172.20.x`? | WSL2 dan VMware dua NAT terpisah; karenanya portproxy + `ADVERTISE_IP`. |

---

## 13. TROUBLESHOOTING NYATA YANG KAMI TEMUI

| Gejala | Penyebab | Solusi |
|---|---|---|
| `ERR\|BOB belum mendaftar ke KDC` | urutan `d` terbalik | `d` di Bob dulu, baru di Alice |
| Alice diam lama setelah `OK-TICKET` | menunggu `CHAL4` dari Bob (Bob tidak dalam mode `d`) | batas tunggu 300 dtk; ulangi `d` di Bob lalu `d` di Alice |
| `ConnectionRefusedError` ke `192.168.59.1:4444` | portproxy hilang / IP WSL berubah | `netsh interface portproxy show all`; jalankan ulang `iziin-bob.ps1` sebagai admin |
| `ping 192.168.59.1` dari VM gagal padahal TCP jalan | Windows profil **Public** memblokir ICMP masuk | jangan pakai ping untuk uji; pakai `wget -q -O /dev/null http://192.168.59.1:8000/proyek.zip` |
| `apk: unable to select package` | `/etc/apk/repositories` di ISO live isinya baris berkomentar semua | jangan pakai apk: gunakan `mulai-bob-lokal.sh` (tarball) |
| `GAGAL membongkar pkg.tar.gz` | format `.apk` Alpine 3.20 = satu tar.gz berisi file langsung | `tar -xzf file.apk -C /`; di proyek ini sudah digabung jadi `alpine-python3.tgz` |
| Dependensi python3 cuma 3 paket | field `C:` di APKINDEX = **checksum**, provides ada di `p:` | resolver sudah dibetulkan → 17 paket |
| VM tidak bisa `apk update` ke dl-cdn | NAT kampus memotong keluar; host bisa, VM tidak | semua berkas diambil dari laptop (VMnet8), VM tidak butuh internet |
| `/root/proyek` hilang | Alpine live jalan di RAM; VM di-restart | tempel ulang dua blok §6.3 |
| Bob daftar dengan IP salah | KDC melihat alamat host (portproxy), bukan alamat VM | `--advertise-ip <ip-eth0-nya>` (otomatis di skrip) |
| `PermissionError` bind port | dua proses memakai port sama | tutup duplikatnya; satu KDC saja |
| Wireshark 0 paket | interface salah (sniff `Ethernet`/loopback) | centang VMnet8 + vEthernet (WSL) |
| Wireshark tidak menampilkan interface | dibuka sebelum Npcap selesai dipasang | tutup dan buka lagi; cek `dumpcap.exe -D` |
| `python -m pytest tests` gagal 1 | port 4444/5555 dipakai proses demo | hentikan demo, jalankan ulang tes |

---

## 14. KETERBATASAN DAN KESIMPULAN

**Keterbatasan yang kami akui (jangan disembunyikan, justru jadi nilai):**

1. **ECB** — dua blok plaintext identik menghasilkan ciphertext identik; pola data masih terlihat.
   Perbaikan: CBC/CTR + IV, atau GCM kalau butuh integritas.
2. **Tidak ada integritas/MAC** — penyadap tidak bisa *membaca*, tapi bisa *membuang* atau mengacak
   ciphertext (dekripsi gagal). Perbaikan: HMAC/CBC-MAC manual.
3. **KDC single point of trust** — KDC memegang semua master key; kalau kompromi, seluruh sesi terbuka.
4. **Tantangan satu arah** (`N_b+1`) — versi penuh Needham–Schroeder menantang dua arah; dan skema ini
   rentan serangan terhadap identitas di langkah 1–2 (sebab itulah ada Needham–Schroeder-Lowe).
5. **Tanpa perfect forward secrecy** — `K_ab` terlindungi `K_as`; kalau `K_as` bocor di masa depan,
   rekaman sesi lama bisa dibuka.
6. **Session key dibangkitkan dari alphabet ASCII 16 char** → entropi ≈ 96 bit, cukup untuk demo,
   lebih kecil daripada 128 bit kunci acak penuh.

**Kesimpulan.** Distribusi kunci memakai KDC terbukti bekerja pada tiga IP berbeda: `K_ab` dibuat KDC,
diantar ke Alice terenkripsi `K_as`, ke Bob lewat tiket terenkripsi `K_bs`, lalu kedua sisi saling
membuktikan kepemilikan kunci lewat nonce (langkah 4–5). Setelah itu komunikasi dua arah berjalan
dengan AES-128 implementasi manual — dibuktikan cocok dengan vektor known-answer FIPS-197 — dan key
masih bisa diganti di tengah jalan tanpa restart. Di Wireshark, yang lewat di jaringan hanya heks:
plaintext chat dan session key tidak pernah terlihat.

---

## 15. REFERENSI DAN PERNYATAAN ORISINALITAS

| Sumber | Jenis | Diambil untuk |
|---|---|---|
| **PPT kelas KDC** (Keamanan Informasi) | acuan skenario — **yang dinilai** | urutan langkah 1–5, notasi `K_as`/`K_bs`/`K_ab` |
| **FIPS PUB 197** (NIST, Advanced Encryption Standard) | standar | struktur round (§5.1–5.3), key expansion, S-Box, vektor known-answer Lampiran C |
| Catatan kuliah Keamanan Informasi | catatan kelas | definisi master key, tiket, alasan nonce/timestamp |

> Salinan PPT kelas dan FIPS-197 **belum dimasukkan ke folder `references/`** — letakkan kedua berkas itu
> di sana sebelum laporan dikumpulkan, supaya penilai bisa mengecek klaim "skenario mengikuti PPT".

**Aturan yang kami pegang:** konsep diambil dari sumber resmi (NIST, PPT kelas), **kode ditulis sendiri**
dan setiap barisnya bisa dijelaskan. Tidak ada satu pun implementasi AES/KDC milik orang lain yang
disalin — komentar di `src/ksilib/aes/` merujuk pasal FIPS-197, bukan menyalin repo.
Perpustakaan yang dipakai hanya: `socket`, `threading`, `secrets`, `argparse`, `time`, `os`, `struct`,
`binascii`. **Tidak ada** `cryptography`, `pycryptodome`, `Crypto.*`, `Fernet`.

---

## 16. LAMPIRAN

### A. Berkas konfigurasi

```ini
# config/hosts/kdc.env
KDC_PORT=4444
SESSION_KEY_LEN=16
SESSION_KEY_TTL_SECONDS=0
MASTER_KEY_ALICE=KasMasterKeyAAAA
MASTER_KEY_BOB=KbsMasterKeyBBBB

# config/hosts/alice.env
KDC_IP=172.20.93.6        # <- satu-satunya baris yang diedit kalau IP WSL berubah
KDC_PORT=4444
CHAT_PORT=5555
ADVERTISE_IP=192.168.59.1 # alamat yang bisa diroute VM Bob
MASTER_KEY=KasMasterKeyAAAA

# config/hosts/bob.env
KDC_IP=192.168.59.1       # portproxy di host -> WSL
CHAT_PORT=5555
ADVERTISE_IP=192.168.59.10 # ditimpa otomatis oleh --advertise-ip di VM
MASTER_KEY=KbsMasterKeyBBBB
```

Key tidak pernah ditulis di dalam `.py`; `.env` asli tidak di-commit.

### B. Skrip bantu

| Skrip | Guna |
|---|---|
| `scripts/vm/iziin-bob.ps1` (admin) | portproxy 4444 + firewall 4444/5555/8000 |
| `scripts/vm/kemas-dan-serve.py` | bikin `vm/proyek.zip` lalu serve `vm/` di `0.0.0.0:8000` |
| `scripts/vm/mirror-apk.py` | unduh closure `python3` Alpine ke `vm/repo/` |
| `scripts/vm/rakit-python3.py` | gabungkan repo jadi `vm/alpine-python3.tgz` |
| `scripts/demo/rehearse.py` | gladi protokol otomatis di 127.0.0.1 |
| `scripts/probe/listen.py` / `send.py` | uji TCP antar perangkat |
| `vm/mulai-bob-lokal.sh` | jalankan Bob tanpa internet (rute utama) |
| `vm/mulai-bob.sh` | rute lama lewat internet (cadangan) |

### C. Bersih-bersih setelah demo

```powershell
netsh interface portproxy delete v4tov4 listenaddress=192.168.59.1 listenport=4444
netsh advfirewall firewall delete rule name="ksi-port-4444"
netsh advfirewall firewall delete rule name="ksi-port-5555"
netsh advfirewall firewall delete rule name="ksi-port-8000"
```

### D. Bukti yang ikut dikumpulkan

```
report/bab-4-hasil/log-kdc-wsl-20261027.txt      log KDC (pembuatan session key)
report/bab-4-hasil/log-bob-windows-20261027.txt  log sisi pasangan (key sama)
report/bab-4-hasil/gladi-{kdc,alice,bob}-20261027-1819.txt   hasil gladi 3 proses
captures/kdc.log · captures/alice.log · captures/bob.log     log live paling akhir
captures/demo.pcapng                                          tangkapan Wireshark (syarat no.6)
```

Selalu beri caption pada screenshot: perangkat mana, jam, langkah keberapa.
