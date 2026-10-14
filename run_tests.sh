#!/usr/bin/env bash
# ==============================================================================
# run_tests.sh — Skrip Pengujian Otomatis Modul Penilai Mutu Beras
# ==============================================================================
# Menjalankan:
# 1. 20 Unit test kasus batas (test_quality_engine.py)
# 2. Tolok ukur kinerja komputasi dan memori NFR (benchmark_performance.py)
# 3. Uji integrasi CLI dan penerbitan sertifikat PDF
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "======================================================================"
echo " PENGUJIAN OTOMATIS MODUL PERANGKAT LUNAK PENILAI MUTU BERAS"
echo " Standar SNI 6128:2020 & Bapanas No. 67/2024"
echo "======================================================================"

echo ""
echo "[1/3] Menjalankan 20 Skenario Unit Test..."
python3 -m unittest discover -s "${SCRIPT_DIR}/tests" -p "test_*.py" -v

echo ""
echo "[2/3] Menjalankan Pengujian Tolok Ukur Kinerja NFR (1.000 Iterasi)..."
python3 "${SCRIPT_DIR}/benchmark_performance.py"

echo ""
echo "[3/3] Menjalankan Uji Asap Integrasi CLI & Ekspor PDF..."
python3 "${SCRIPT_DIR}/cli.py" --ka 13.5 --bp 14.0 --mn 0.4 --ba 0.008 --id "Uji-Integrasi-Otomatis" --save --pdf

echo ""
echo "======================================================================"
echo " SELURUH PENGUJIAN BERHASIL LULUS 100%!"
echo " Modul siap digunakan untuk operasional luring dan demonstrasi UAS."
echo "======================================================================"
