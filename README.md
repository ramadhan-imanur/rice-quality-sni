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

## Struktur Repositori (Standard Industry src/ Layout)

```text
code/
├── src/                          # Paket sumber kode inti (Domain & Application Logic)
│   ├── __init__.py               # Deklarasi paket & re-ekspor API publik
│   ├── quality_engine.py         # Domain Core: Aturan SNI 6128:2020, klasifikasi O(1), penyesuaian Bapanas
│   ├── cv_engine.py              # Computer Vision: Otsu segmentation, tensor inersia orde-2, filter butir
│   ├── database.py               # Data Persistence: SQLite, PBKDF2 hashing, HMAC-SHA256, Audit logs
│   ├── pdf_generator.py          # Document Service: Raw PDF 1.4, vektor QR ISO/IEC 18004, stempel digital
│   ├── qr_codec.py               # Security Codec: Matriks QR Code mandiri tanpa dependensi pihak ketiga
│   ├── api_server.py             # HTTP Gateway: Multithreaded REST API & peladen berkas statis
│   └── cli.py                    # Terminal Interface: Wizard interaktif & eksekusi one-liner script
├── web/                          # Klien antarmuka web responsif (< 85 KB, offline-first)
│   ├── index.html                # Single-Page App: 4 Tab (Simulasi/CV, Maker, Checker, Arsip)
│   ├── verify.html               # Portal publik verifikasi integritas taksasi
│   ├── style.css                 # Desain UI agritech, deteksi preview, traffic-light gauges
│   └── app.js                    # Pengendali kamera CV, tab, REST API fetch, & visualisasi
├── scripts/                      # Skrip otomasi, tolok ukur, & utilitas pengembang
│   ├── benchmark_performance.py  # Tolok ukur latensi (perf_counter) & RAM (tracemalloc)
│   ├── run_tests.sh              # Skrip runner otomatis untuk seluruh 39 unit test & benchmark
│   └── run_e2e_tests.sh          # Skrip runner otomatis untuk suite pengujian browser Playwright
├── tests/                        # Suite pengujian komprehensif
│   ├── __init__.py
│   ├── unit/                     # 39 Pengujian unit deterministik & audit keamanan
│   │   ├── __init__.py
│   │   ├── test_quality_engine.py# 20 kasus batas toleransi SNI
│   │   ├── test_maker_checker.py # 6 skenario alur Maker-Checker & Anti-Fraud HMAC
│   │   ├── test_cv_engine.py     # 6 skenario segmentasi & akurasi dimensi butir CV
│   │   └── test_security_hardened.py # 7 skenario audit keamanan (OWASP, DoS, Rate Limit, UU PDP)
│   └── e2e/                      # Pengujian End-to-End browser Playwright (Multi-Viewport)
│       ├── pages/                # Page Object Models (Dashboard, Maker, Checker, Verify)
│       ├── test_app_flows.spec.js# 18 pengujian E2E (Desktop 1280px & Mobile 375px)
│       ├── capture_screenshots.js# Utilitas dokumentasi visual
│       └── screenshots/          # Tangkapan layar otomatis antarmuka
├── data/                         # Basis data & berkas persistensi
│   ├── rice_sni.db               # Basis data SQLite terpusat untuk integritas lembar taksasi
│   └── lab_samples.json          # Basis data riwayat pengujian sampel format JSON
├── docs/                         # Spesifikasi teknis & dokumentasi sistem
│   ├── ARCHITECTURE.md           # Peta arsitektur & panduan direktori pengembang
│   └── DESIGN.md                 # Pedoman desain UI/UX agritech & token palet
├── output/                       # Direktori keluaran berkas PDF taksasi lokal & label pengantar
│   └── .gitkeep                  # Menjaga direktori tetap terlacak di Git
├── supabase/                     # Skema migrasi komputasi awan (PostgreSQL)
│   └── migrations/
│       ├── 20261016_init_rls.sql # Skema RLS dasar & fungsi verifikasi publik
│       └── 20261016_hardening.sql# Optimasi RLS JWT Metadata, Indeks Komposit, & Trigger Audit
├── .env.example                  # Templat konfigurasi lingkungan produksi
├── Makefile                      # Task runner pengembang (make test, make run, dll.)
├── pyproject.toml                # Standar konfigurasi proyek Python & pytest
├── requirements.txt              # Spesifikasi dependensi Python
├── package.json                  # Dependensi Node.js / Playwright
├── playwright.config.js          # Konfigurasi pengujian browser multi-viewport
└── README.md                     # Gerbang dokumentasi utama repositori
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
python3 src/cli.py
```

Atau evaluasi langsung via argumen parameter baris perintah:
```bash
python3 src/cli.py --ka 13.5 --bp 14.0 --mn 0.4 --ba 0.008 --id "Beras IR64 Super" --save --pdf
```

Melihat riwayat pengujian lokal:
```bash
python3 src/cli.py --history
```

### 2. Antarmuka Web & Peladen REST API (`src/api_server.py` & `web/`)

Jalankan peladen REST API terpadu (menyajikan antarmuka Maker-Checker, database SQLite, dan endpoint verifikasi publik):
```bash
# Menggunakan Makefile (Direkomendasikan)
make run

# Atau langsung via Python
python3 src/api_server.py
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
# Melalui Makefile (Direkomendasikan)
make test
make test-e2e

# Atau langsung via skrip otomasi
bash scripts/run_tests.sh
bash scripts/run_e2e_tests.sh
```

Atau jalankan masing-masing komponen pengujian secara mandiri:
```bash
# 1. 39 Unit test kasus batas logika SNI, alur Maker-Checker, CV Engine & Hardening Keamanan
python3 -m unittest discover -s tests/unit -p "test_*.py" -v

# 2. Tolok ukur kinerja NFR (1.000 iterasi)
python3 scripts/benchmark_performance.py

# 3. Pengujian E2E Multi-Viewport Playwright (18 pengujian)
npx playwright test
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
