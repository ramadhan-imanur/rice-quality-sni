#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/index.py — Vercel Serverless Function Entrypoint
====================================================
Menjembatani endpoint /api/* pada Vercel dengan RiceQualityAPIHandler.
Mendukung klasifikasi deterministik O(1) SNI 6128:2020, kalkulator harga Bapanas 67/2024,
analisis CV fisik beras, alur Maker-Checker, dan verifikasi sertifikat publik anti-fraud.

Penulis: Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi: MIT
"""

import os
import sys

# Konfigurasi PYTHONPATH untuk menyertakan src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api_server import RiceQualityAPIHandler
from database import DEFAULT_DB_PATH, init_db

# Pastikan basis data terinisialisasi jika berada di lingkungan serverless
if os.environ.get("VERCEL"):
    os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
    if not os.path.exists(DEFAULT_DB_PATH) or os.path.getsize(DEFAULT_DB_PATH) == 0:
        try:
            init_db(DEFAULT_DB_PATH)
        except Exception as e:
            sys.stderr.write(f"Warning: Gagal inisialisasi basis data serverless: {e}\n")

# Handler class standar Vercel Python runtime
class handler(RiceQualityAPIHandler):
    pass
