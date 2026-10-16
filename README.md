# Rice Quality Grader & Digital Certificate Engine (SNI 6128:2020)
### Sistem Penilai Mutu Beras Deterministik $\mathcal{O}(1)$ & Generator Sertifikat Digital Berbiaya Rp 0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Standards: SNI 6128:2020](https://img.shields.io/badge/Standard-SNI%206128%3A2020-green.svg)](https://bsn.go.id)
[![Regulation: Bapanas 67/2024](https://img.shields.io/badge/Regulasi-Bapanas%20No.%2067%2F2024-red.svg)](https://badanpangan.go.id)
[![Zero-Dependency](https://img.shields.io/badge/Dependencies-Zero%20(Pure%20Stdlib)-brightgreen.svg)](#arsitektur-sistem)
[![Latency](https://img.shields.io/badge/Latency-1.17%20ms-informational.svg)](#hasil-verifikasi-kebutuhan-non-fungsional-nfr)

Aplikasi perangkat lunak agritech deterministik untuk penilaian mutu beras terstandar dan kalkulator harga acuan resmi pemerintah Indonesia. Dirancang khusus untuk memitigasi asimetri informasi dan taksiran sepihak tengkulak di tingkat petani produsen, kios beras, dan unit penggilingan padi kecil (RMU).

Sistem beroperasi **100% luring (*offline-first*)**, tanpa dependensi pustaka pihak ketiga (*zero external dependencies*), dengan konsumsi memori hemat (< 13 MB), dan biaya sewa server **Rp 0**.

---

## Daftar Isi
- [Fitur Utama](#fitur-utama)
- [Struktur Repositori](#struktur-repositori)
- [Landasan Aturan & Logika Keputusan](#landasan-aturan--logika-keputusan)
  - [A. Batas Toleransi Mutu SNI 6128:2020](#a-tabel-batas-toleransi-baku-sni-61282020)
  - [B. Formula Penyesuaian Harga Bapanas No. 67/2024](#b-formula-penyesuaian-harga-resmi-bapanas-no-672024)
- [Petunjuk Penggunaan](#petunjuk-penggunaan)
  - [1. Antarmuka Terminal (CLI)](#1-antarmuka-terminal-interaktif-cli)
  - [2. Antarmuka Web Luring](#2-antarmuka-web-luring-web)
  - [3. Eksekusi Pengujian & Benchmark](#3-eksekusi-pengujian--benchmark)
- [Hasil Verifikasi Non-Fungsional (NFR)](#hasil-verifikasi-kebutuhan-non-fungsional-nfr)
- [Model Monetisasi & Bisnis UMKM](#model-monetisasi--bisnis-umkm)
- [Identitas Pengembang & Sitasi](#identitas-pengembang--sitasi)
- [Lisensi](#lisensi)

---

## Fitur Utama

1. **Mesin Klasifikasi Deterministik $\mathcal{O}(1)$ (`quality_engine.py`):**
   - Validasi batas ketat untuk 4 parameter fisik beras (Kadar Air, Butir Patah, Butir Menir, Benda Asing).
   - Pengelompokan bertingkat ke dalam 4 kelas mutu: **Premium**, **Medium I**, **Medium II**, dan **Substandar**.
   - Formula penalti pengeringan dan penyusutan bobot berdasarkan regulasi resmi Badan Pangan Nasional No. 67/2024.
2. **Generator Sertifikat PDF Murni (`pdf_generator.py`):**
   - Menghasilkan dokumen resmi 1 halaman PDF ukuran A4 standar secara instan (< 1 detik) tanpa memerlukan pustaka berat pihak ketiga seperti ReportLab atau WeasyPrint (murni *raw PDF 1.4 stream*).
   - Dilengkapi nomor seri sertifikat berurutan, tabel deviasi parameter, stempel mutu, dan rekomendasi harga transaksi.
3. **Antarmuka Web Statis Luring (`web/`):**
   - Berukuran sangat ringan (< 60 KB), responsif untuk peramban ponsel Android maupun desktop.
   - Fitur kustomisasi kop surat nama toko/penggilingan beras untuk pedagang eceran.
   - Cetak lembar sertifikat resmi siap pajang melalui dialog cetak peramban (`Ctrl+P` / *Save as PDF*).
   - Penyimpanan riwayat pengujian lokal berbasis `localStorage` dengan tombol ekspor data format JSON.
   - Slot pemesanan paket starter kit dan promosi mitra agribisnis via WhatsApp.
4. **Antarmuka Baris Perintah Interaktif & Otomasi (`cli.py`):**
   - Modus wizard interaktif ramah pemula atau eksekusi *one-liner flag* untuk integrasi skrip.

---

## Struktur Repositori

```text
rice-quality-sni/
├── quality_engine.py         # Modul inti Python: validasi, klasifikasi SNI, kalkulasi harga Bapanas
├── cv_engine.py              # Mesin Computer Vision: segmentasi Otsu, tensor inersia orde-2, klasifikasi butir
├── database.py               # Lapisan persistensi SQLite (Users, Submissions, Certificates, Audit Logs) & HMAC
├── qr_codec.py               # Generator matriks QR Code ISO/IEC 18004 murni (Zero External Dependencies)
├── pdf_generator.py          # Generator Lembar Taksasi Mutu PDF A4 (QR vektor, segel HMAC, watermark, disclaimer UU)
├── api_server.py             # Peladen REST API & Backend Maker-Checker + Computer Vision (Pustaka Standar Python)
├── cli.py                    # Antarmuka CLI interaktif & otomasi terminal
├── benchmark_performance.py  # Skrip tolok ukur latensi, alokasi heap RAM, dan ukuran berkas
├── run_tests.sh              # Skrip runner otomatis untuk seluruh 32 pengujian unit & benchmark
├── requirements.txt          # Spesifikasi dependensi (Pustaka Standar Python 3.8+ / Pillow, NumPy, SciPy untuk CV)
├── LICENSE                   # Lisensi sumber terbuka MIT
├── data/
│   ├── rice_sni.db           # Basis data SQLite terpusat untuk integritas lembar taksasi
│   └── lab_samples.json      # Basis data riwayat pengujian sampel format JSON
├── output/
│   └── .gitkeep              # Direktori keluaran berkas PDF taksasi lokal & label pengantar
├── tests/
│   ├── __init__.py
│   ├── test_quality_engine.py # 20 skenario unit test kasus batas toleransi SNI
│   ├── test_maker_checker.py  # 6 skenario unit test arsitektur Maker-Checker & Anti-Fraud
│   └── test_cv_engine.py      # 6 skenario unit test Computer Vision & tensor inersia
└── web/                      # Antarmuka web responsif (< 85 KB)
    ├── index.html            # Portal 4-Tab: Simulasi + CV, Maker Petani, Checker Lab, Bank Taksasi
    ├── verify.html           # Portal publik verifikasi keaslian dokumen taksasi via QR Code / HMAC
    ├── style.css             # Desain UI, deteksi CV preview, traffic-light gauges, & stylesheet cetak A4
    └── app.js                # Pengendali kamera CV, tab, REST API fetch, & visualisasi interaktif
```

---

## Landasan Aturan & Logika Keputusan

### A. Tabel Batas Toleransi Baku SNI 6128:2020
Evaluasi dilakukan berjenjang: Premium $\to$ Medium I $\to$ Medium II $\to$ Substandar.

| Kelas Mutu | Kadar Air Maks (%) | Butir Patah Maks (%) | Butir Menir Maks (%) | Benda Asing Maks (%) |
| :--- | :---: | :---: | :---: | :---: |
| **PREMIUM** | $\le 14,0$ | $\le 15,0$ | $\le 0,5$ | $\le 0,01$ |
| **MEDIUM I** | $\le 14,0$ | $\le 20,0$ | $\le 2,0$ | $\le 0,02$ |
| **MEDIUM II** | $\le 14,0$ | $\le 25,0$ | $\le 5,0$ | $\le 0,05$ |
| **SUBSTANDAR** | $> 14,0$ *(atau melampaui batas fisik di atas)* | — | — | — |

### B. Formula Penyesuaian Harga Resmi (Bapanas No. 67/2024)
1. **Harga Dasar per Kelas Mutu:**
   - Premium: Rp 15.800 / kg (HET Beras Premium)
   - Medium I: Rp 13.500 / kg (HET Beras Medium)
   - Medium II: Rp 13.500 / kg (HET Beras Medium)
   - Substandar: Rp 11.500 / kg (HPP Beras)
2. **Kelebihan Kadar Air:**
   $$\Delta KA = \max(0, KA - 14,0)$$
3. **Penalti Biaya Pengeringan:**
   $$P_{\text{kering}} = \Delta KA \times \text{Rp } 150 \text{ per kg}$$
4. **Potongan Penyusutan Bobot (1,5% per 1% $\Delta KA$):**
   $$P_{\text{susut}} = \Delta KA \times 0,015 \times \text{Harga Dasar}$$
5. **Rekomendasi Harga Bersih Pembelian:**
   $$\text{Harga Bersih} = \max(0, \text{Harga Dasar} - P_{\text{kering}} - P_{\text{susut}})$$

---

## Petunjuk Penggunaan

### 1. Antarmuka Terminal Interaktif (CLI)

Jalankan wizard interaktif:
```bash
python3 cli.py
```

Atau evaluasi langsung via argumen parameter baris perintah:
```bash
python3 cli.py --ka 13.5 --bp 14.0 --mn 0.4 --ba 0.008 --id "Beras IR64 Super" --save --pdf
```

Melihat riwayat pengujian lokal:
```bash
python3 cli.py --history
```

### 2. Antarmuka Web & Peladen REST API (`api_server.py` & `web/`)

Jalankan peladen REST API terpadu (menyajikan antarmuka Maker-Checker, database SQLite, dan endpoint verifikasi publik):
```bash
# Jalankan peladen resmi backend + web
python3 api_server.py
```
Akses melalui peramban:
- **Aplikasi Utama (Maker-Checker & Simulasi):** `http://localhost:8000/`
- **Portal Cek Keaslian Publik (Anti-Fraud Verifier):** `http://localhost:8000/verify.html`

*Aplikasi web juga tetap dapat berjalan 100% luring mandiri tanpa server cukup dengan membuka berkas `web/index.html` langsung di peramban.*

**Fitur Cetak Sertifikat A4:**  
Setelah memasukkan parameter dan menekan tombol *Evaluasi Mutu*, tekan tombol **Cetak / Simpan Sertifikat Resmi PDF (A4)** atau tekan tombol `Ctrl + P` pada keyboard peramban untuk mencetak lembar sertifikat resmi atau menyimpannya sebagai file PDF.

### 3. Eksekusi Pengujian & Benchmark

Jalankan seluruh rangkaian uji dalam sekali jalan:
```bash
./run_tests.sh
```

Atau jalankan masing-masing komponen pengujian secara mandiri:
```bash
# 1. 20 Unit test kasus batas logika SNI
python3 -m unittest discover -s tests -p "test_*.py" -v

# 2. Tolok ukur kinerja NFR (1.000 iterasi)
python3 benchmark_performance.py
```

---

## Hasil Verifikasi Kebutuhan Non-Fungsional (NFR)

Berdasarkan pengujian tolok ukur 1.000 iterasi (`benchmark_performance.py`):

| Kriteria NFR | Hasil Pengujian | Ambang Batas PRD | Status |
| :--- | :---: | :---: | :---: |
| **NFR-01: Ukuran Bundel Kode Program** | 44,32 KB (Python) + 57 KB (Web) | $< 1,00$ MB | **Lulus** |
| **NFR-02: Konsumsi Memori Puncak (RAM)** | 0,009 MB heap (~12,8 MB proses) | $< 40,00$ MB | **Lulus** |
| **NFR-03: Latensi Komputasi Logika** | 1,17 ms per sampel | $< 10,00$ ms | **Lulus** |
| **NFR-04: Biaya Komputasi Server** | Rp 0 (100% Offline-First) | Rp 0 | **Lulus** |
| **NFR-05: Waktu Operasi Pengguna** | 25–45 detik | $< 90$ detik | **Lulus** |

---

## Model Monetisasi & Bisnis UMKM

Sistem ini dirancang tidak hanya sebagai modul teknis, melainkan memiliki kelayakan bisnis mandiri (*freemium economics*):

1. **Paket Hardware-Software Bundling Kit (Starter Pack UMKM):**  
   Menjual paket siap pakai untuk penggilingan padi desa dan kios pasar: 1 unit Moisture Tester Digital + 1 unit Timbangan Saku Presisi 0.01g + Akses Web & Panduan SNI. Margin laba bersih: **Rp 200.000 – Rp 250.000 per paket**. Titik impas (BEP) tercapai hanya dengan 3 unit terjual.
2. **Jasa Sertifikasi & Cetak Kios Beras:**  
   Menyediakan jasa pengujian fisik dan pencetakan lembar sertifikat mutu ber-Kop toko beras eceran di pasar tradisional (tarif mikro Rp 2.500 – Rp 10.000 per sertifikat laminasi untuk dipajang di etalase/karung beras).
3. **Kustomisasi & White-Labeling BUMDes/KUD:**  
   Jasa pemasangan dan kustomisasi kop surat/logo instansi lokal pada laptop pengelola lumbung pangan desa (tarif setup Rp 350.000 – Rp 500.000 per instansi).
4. **Ruang Iklan Terkurasi (*In-App Ad Placement*):**  
   Slot promosi produk agribisnis lokal (toko sarana pertanian, benih unggul BPSB, dan alat pascapanen) pada antarmuka web versi gratis.

---

## Identitas Pengembang & Sitasi

* **Pengembang Tunggal:** Ramadhaan Imanur Rochima (NIM M0124015)  
* **Program Studi:** S1 Matematika, Fakultas Matematika dan Ilmu Pengetahuan Alam, Universitas Sebelas Maret (UNS), Surakarta  
* **Dosen Pembimbing & Pengampu:** Dr. Sutanto, S.Si., DEA  
* **Mata Kuliah:** Kewirausahaan (09313110203)  
* **Format Sitasi Akademik:**
  > Rochima, R. I., Wira, A. R., & Sutanto. (2026). *Model Aplikasi Penilai Mutu dan Penentuan Harga Beras Tingkat Petani Berbasis Pengukuran Fisik*. Jurnal Bisnis & Kewirausahaan (JBK).

---

## Lisensi

Proyek ini didistribusikan di bawah lisensi terbuka [MIT License](LICENSE). Bebas digunakan, dipelajari, dan dikembangkan kembali untuk kemaslahatan petani dan tata niaga beras berkeadilan di Indonesia.
