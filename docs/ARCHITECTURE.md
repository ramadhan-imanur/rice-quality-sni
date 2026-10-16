# ARSITEKTUR SISTEM & DIREKTORI KODE (ARCHITECTURE.md)
## Sistem Taksasi Mutu Beras SNI 6128:2020 & Anti-Fraud Engine

Dokumen ini menjelaskan arsitektur perangkat lunak, struktur modul, serta aliran data (*data flow*) antar-lapisan sistem.

---

## 1. Peta Direktori Standar Industri (`src/` Layout)

Repositori ini menerapkan tata letak standar Python Packaging Authority (PyPA) yang modular dan teruji di lingkungan produksi:

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
├── web/                          # Klien antarmuka web statis (< 85 KB, offline-first)
│   ├── index.html                # Single-Page App: 4 Tab (Simulasi/CV, Maker, Checker, Arsip)
│   ├── verify.html               # Portal publik verifikasi integritas taksasi
│   ├── style.css                 # Sistem desain agritech, gauge traffic-light, print stylesheet
│   └── app.js                    # Pengendali UI, kamera CV, REST API client, export data
├── scripts/                      # Skrip otomasi, tolok ukur, & utilitas pengembang
│   ├── benchmark_performance.py  # Tolok ukur latensi (perf_counter) & RAM (tracemalloc)
│   ├── run_tests.sh              # Eksekutor 32 unit test, benchmark, & CLI smoke test
│   └── run_e2e_tests.sh          # Eksekutor Playwright browser test
├── tests/                        # Suite pengujian komprehensif
│   ├── __init__.py
│   ├── unit/                     # 32 Pengujian unit deterministik
│   │   ├── __init__.py
│   │   ├── test_quality_engine.py# 20 kasus batas toleransi SNI
│   │   ├── test_maker_checker.py # 6 skenario alur Maker-Checker & HMAC
│   │   └── test_cv_engine.py     # 6 skenario segmentasi & akurasi dimensi butir
│   └── e2e/                      # Pengujian End-to-End browser Playwright
│       ├── test_app_flows.spec.js# Verifikasi 4 alur antarmuka web
│       ├── capture_screenshots.js# Utilitas dokumentasi visual
│       └── screenshots/          # Tangkapan layar antarmuka desktop & mobile
├── data/                         # Persistensi data lokal
│   ├── rice_sni.db               # Basis data SQLite utama
│   └── lab_samples.json          # Riwayat sampel pengujian
├── docs/                         # Spesifikasi teknis & dokumentasi sistem
│   ├── ARCHITECTURE.md           # Peta arsitektur & panduan direktori (berkas ini)
│   └── DESIGN.md                 # Pedoman desain UI/UX agritech & token palet
├── output/                       # Direktori keluaran artefak dokumen PDF
│   └── .gitkeep                  # Menjaga direktori tetap terlacak di Git
├── supabase/                     # Skema migrasi komputasi awan (PostgreSQL)
│   └── migrations/
│       └── 20261016_init_rls.sql # Skema RLS & UU PDP No. 27/2022
├── Makefile                      # Task runner pengembang (make test, make run, dll.)
├── pyproject.toml                # Konfigurasi standar proyek Python & pytest
├── requirements.txt              # Spesifikasi dependensi Python
├── package.json                  # Dependensi Node.js / Playwright
├── playwright.config.js          # Konfigurasi pengujian browser
└── README.md                     # Gerbang dokumentasi utama repositori
```

---

## 2. Aliran Data Arsitektur (*Data Flow*)

```text
[Kamera Web / Input Manual] ──> [web/app.js]
                                      │ (HTTP POST JSON / Multipart)
                                      ▼
                             [src/api_server.py]
                                      │
              ┌───────────────────────┼────────────────────────┐
              ▼                       ▼                        ▼
     [src/cv_engine.py]     [src/quality_engine.py]   [src/database.py]
   (Segmentasi Otsu &        (Klasifikasi O(1) &       (SQLite + Jejak Audit +
    Tensor Inersia Orde-2)    Kalkulasi Bapanas)        Tanda Tangan HMAC)
              │                       │                        │
              └───────────────────────┼────────────────────────┘
                                      ▼
                            [src/pdf_generator.py]
                                      │
                                      ▼
                        [output/taksasi_*.pdf]
                         (Dokumen Resmi A4 + QR)
```

---

## 3. Kompatibilitas Mundur (*Backward Compatibility*)

Untuk menjamin kelancaran perintah eksekusi dari dokumen silabus perkuliahan (`RPS.pdf`), PRD, maupun *roadmap* tim:
* Modul di root (`code/quality_engine.py`, `code/api_server.py`, `code/cli.py`, `code/database.py`, `code/pdf_generator.py`, `code/cv_engine.py`, `code/qr_codec.py`) berfungsi sebagai **shim re-ekspor transparan** yang merujuk langsung ke `src/`.
* Eksekusi lama seperti `python3 api_server.py` atau `python3 cli.py` tetap berjalan 100% normal tanpa galat.
