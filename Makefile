# ==============================================================================
# Makefile — Sistem Taksasi Mutu Beras Digital SNI 6128:2020 & Bapanas 67/2024
# ==============================================================================

.PHONY: help install test test-e2e benchmark run clean

PYTHON ?= python3

help:
	@echo "Perintah yang tersedia:"
	@echo "  make install    - Memasang dependensi Python dan Playwright"
	@echo "  make test       - Menjalankan 32 skenario pengujian unit deterministik"
	@echo "  make benchmark  - Menjalankan tolok ukur kinerja NFR (1.000 iterasi)"
	@echo "  make test-e2e   - Menjalankan pengujian antarmuka browser Playwright"
	@echo "  make run        - Menjalankan peladen REST API & antarmuka web"
	@echo "  make clean      - Membersihkan berkas cache, pycache, dan artefak uji"

install:
	$(PYTHON) -m pip install -r requirements.txt
	@if [ -f package.json ]; then npm install; fi

test:
	@echo "[*] Menjalankan Suite Pengujian Unit..."
	bash scripts/run_tests.sh

benchmark:
	@echo "[*] Menjalankan Benchmark NFR..."
	$(PYTHON) scripts/benchmark_performance.py

test-e2e:
	@echo "[*] Menjalankan Pengujian E2E Browser..."
	bash scripts/run_e2e_tests.sh

run:
	@echo "[*] Menjalankan Peladen REST API di http://localhost:8000/..."
	$(PYTHON) src/api_server.py

clean:
	@echo "[*] Membersihkan cache dan berkas sementara..."
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ tests/unit/__pycache__ tests/e2e/__pycache__
	rm -rf .pytest_cache test-results playwright-report tests/e2e/playwright-report
	rm -f output/*.pdf
	@echo "[✓] Direktori bersih."
