#!/usr/bin/env bash
# ==============================================================================
# Skrip Otomatisasi Pengujian End-to-End (E2E) Playwright
# Sistem Taksasi Mutu Beras SNI 6128:2020 & Anti-Fraud Engine
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

echo "======================================================================"
echo " MENJALANKAN SUITE PENGUJIAN END-TO-END (E2E) PLAYWRIGHT"
echo " Alur: Navigasi, Form Maker, CV Engine, Checker Lab, & Verifikasi Publik"
echo "======================================================================"

# Periksa apakah peladen berjalan di port 8000
if ! curl -sI http://localhost:8000/ > /dev/null; then
    echo "[!] Peladen web belum aktif di port 8000. Memulai api_server.py..."
    python3 api_server.py &
    SERVER_PID=$!
    sleep 2
    trap "kill $SERVER_PID 2>/dev/null || true" EXIT
else
    echo "[✓] Peladen web terdeteksi aktif di http://localhost:8000/"
fi

# Jalankan Playwright Test
if [ -d "/tmp/pw-test/node_modules" ]; then
    NODE_PATH=/tmp/pw-test/node_modules /tmp/pw-test/node_modules/.bin/playwright test --config "${ROOT_DIR}/playwright.config.js"
else
    npx playwright test --config "${ROOT_DIR}/playwright.config.js"
fi

echo "======================================================================"
echo " [✓] SELURUH PENGUJIAN E2E BERHASIL LULUS 100%!"
echo "======================================================================"
