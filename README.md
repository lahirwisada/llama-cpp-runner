# Llama.cpp Runner

Aplikasi berbasis GUI menggunakan Python dan Tkinter untuk memudahkan pengelolaan dan eksekusi model AI Llama.cpp di sistem operasi Linux (khususnya MX Linux) dan Windows.

## Deskripsi

Llama.cpp Runner dirancang untuk pengguna yang menginginkan antarmuka visual sederhana untuk menjalankan model bahasa besar (LLM) dalam format GGUF. Aplikasi ini memungkinkan pengguna untuk memilih lokasi binary llama.cpp, memilih file model, mengatur parameter performa seperti jumlah thread dan context size, serta memilih mode eksekusi antara Server (untuk akses via browser) atau CLI (Command Line Interface).

Fitur utama aplikasi ini mencakup deteksi otomatis proses yang sedang berjalan dan kemampuan untuk membersihkan memori dengan menghentikan proses yang menggantung, sehingga sangat cocok untuk sistem dengan sumber daya terbatas.

## Fitur Utama

- Pemilihan lokasi folder bin Llama.cpp secara manual
- Pemilihan file model (.gguf) melalui file dialog
- Konfigurasi parameter performa:
  - Threads (-t)
  - Context size (-c)
  - Predict tokens (-n)
  - Port server (--port)
- Pilihan mode eksekusi: Server (WebUI) atau CLI
- Deteksi status proses Llama.cpp yang sedang berjalan
- Fungsi Stop and Clean Memory untuk menghentikan proses dan membebaskan RAM
- Dukungan lintas platform (Linux dan Windows)

## Persyaratan Sistem

### Untuk MX Linux / Linux Umum
1. Python 3.x
2. Library tkinter (`python3-tk`)
3. Library psutil (`pip install psutil`)
4. Binary Llama.cpp yang sudah di-compile (folder `build/bin`)

### Untuk Windows
1. Python 3.x
2. Library tkinter (biasanya sudah termasuk dalam instalasi Python standar)
3. Library psutil (`pip install psutil`)
4. Binary Llama.cpp yang sudah di-compile (file `.exe` di folder `bin` atau `Release`)

## Cara Instalasi

1. Pastikan Python 3 sudah terinstal di sistem Anda.
2. Instal dependensi yang diperlukan melalui terminal:

```bash
sudo apt update
sudo apt install python3-tk python3-pip
pip3 install psutil
```

3. Unduh atau salin script `llama-cpp-runner.py` ke direktori pilihan Anda.

## Cara Penggunaan

1. Jalankan aplikasi melalui terminal:

```bash
python3 llama-cpp-runner.py
```

2. Pada antarmuka aplikasi:
   - Klik tombol Browse di bagian Folder Bin Llama.cpp dan arahkan ke direktori tempat binary llama.cpp berada (contoh: `/media/2019DATA/www/llama.cpp/build/bin`).
   - Klik tombol Browse di bagian File Model dan pilih file model dengan ekstensi .gguf.
   - Atur nilai Threads sesuai dengan jumlah core CPU Anda untuk performa optimal.
   - Pilih mode eksekusi yang diinginkan (Server atau CLI).

3. Klik tombol Run Llama.cpp untuk memulai.

4. Jika Anda ingin menutup aplikasi runner tetapi tetap membiarkan AI berjalan, Anda dapat menutup jendela aplikasi. Proses akan tetap berjalan di latar belakang.

5. Untuk menghentikan proses dan membersihkan memori, buka kembali aplikasi dan klik tombol Stop and Clean Memory.

## Struktur Kode

Kode disusun secara modular dengan kelas utama `LlamaCppRunner` yang menangani:
- Inisialisasi antarmuka pengguna
- Pengelolaan path dan konfigurasi
- Eksekusi proses subprocess
- Manajemen proses sistem menggunakan psutil

## Catatan Penting

- Pastikan binary llama.cpp sudah di-compile dengan benar sebelum menggunakan aplikasi ini.
- Untuk pengguna CPU-only tanpa GPU, disarankan menggunakan model yang sudah di-quantize (misalnya Q4_K_M) untuk menghemat penggunaan RAM.
- Nilai Threads tidak boleh melebihi jumlah core fisik CPU agar sistem tidak menjadi lambat.

## Lisensi

Proyek ini dibuat untuk tujuan edukasi dan pengembangan pribadi.
