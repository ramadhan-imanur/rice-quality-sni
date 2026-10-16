#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_cv_engine.py — Pengujian Unit Otomatis untuk Computer Vision Engine
========================================================================
Menguji:
1. Generator Citra Butir Sintetik (Synthetic Grain Generator)
2. Segmentasi Ambang Batas Otsu & Pelabelan Komponen Terhubung
3. Perhitungan Momen Sentral & Tensor Inersia Orde-2 (Invarian Rotasi)
4. Klasifikasi Dimensi SNI (Butir Kepala, Butir Patah, Butir Menir, Benda Asing)
5. Penanganan Citra Batas / Ekstrem (Citra Kosong / Hitam Total)
6. Integrasi dengan Quality Engine (Taksasi Mutu SNI & Bapanas)
7. Anotasi Citra Base64 & Bounding Box Visual

Penulis: Ramadhaan Imanur Rochima (NIM M0124015) — S1 Matematika FMIPA UNS
"""

import base64
import io
import math
import os
import sys
import unittest
from PIL import Image, ImageDraw
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (SRC_DIR, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from cv_engine import RiceCVEngine, generate_synthetic_rice_image
from quality_engine import evaluate_sample


class TestRiceCVEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RiceCVEngine(min_grain_area=15, max_grain_area=10000)

    def test_01_synthetic_image_generation(self):
        """Memverifikasi generator citra sintetik menghasilkan gambar RGB valid."""
        img = generate_synthetic_rice_image(width=640, height=480, num_grains=40)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (640, 480))
        self.assertEqual(img.mode, "RGB")

    def test_02_synthetic_image_analysis(self):
        """Memverifikasi analisis citra sintetik mendeteksi butir dan mengklasifikasikan dimensi SNI."""
        img = generate_synthetic_rice_image(width=640, height=480, num_grains=45)
        res = self.engine.analyze_image(img)

        self.assertIn("grain_count", res)
        self.assertIn("persentase_butir_kepala", res)
        self.assertIn("persentase_butir_patah", res)
        self.assertIn("persentase_butir_menir", res)
        self.assertIn("persentase_benda_asing", res)
        self.assertIn("reference_L0_px", res)

        # Butir terdeteksi harus mendekati jumlah sintetik
        self.assertGreater(res["grain_count"], 20)
        self.assertGreater(res["reference_L0_px"], 0)

        # Total persentase harus mendekati 100%
        total_pct = (
            res["persentase_butir_kepala"]
            + res["persentase_butir_patah"]
            + res["persentase_butir_menir"]
            + res["persentase_benda_asing"]
        )
        self.assertAlmostEqual(total_pct, 100.0, delta=0.5)

    def test_03_annotated_image_base64(self):
        """Memverifikasi anotasi citra menghasilkan string base64 JPEG yang valid."""
        img = generate_synthetic_rice_image(width=400, height=300, num_grains=20)
        res = self.engine.analyze_image(img)
        b64 = self.engine.annotate_image(img, res["details"])

        self.assertIsInstance(b64, str)
        self.assertGreater(len(b64), 100)

        # Verifikasi decoded base64 adalah citra JPEG valid
        raw_bytes = base64.b64decode(b64)
        decoded_img = Image.open(io.BytesIO(raw_bytes))
        self.assertEqual(decoded_img.size, (400, 300))

    def test_04_dimension_accuracy_inertia_tensor(self):
        """
        Memverifikasi akurasi tensor inersia orde-2:
        Menggambar sebuah elips putih di latar belakang hitam dengan panjang semi-major a=30 (L=60)
        dan semi-minor b=10 (W=20) yang diputar sudut 45 derajat.
        """
        w, h = 200, 200
        cx, cy = 100, 100
        a, b = 30, 10  # sumbu panjang L = 2*a = 60, sumbu lebar W = 2*b = 20
        theta = math.radians(45)

        # Buat citra hitam dengan elips putih diputar 45 derajat
        arr = np.zeros((h, w), dtype=np.uint8)
        y, x = np.ogrid[:h, :w]
        x_rot = (x - cx) * math.cos(theta) + (y - cy) * math.sin(theta)
        y_rot = -(x - cx) * math.sin(theta) + (y - cy) * math.cos(theta)
        mask = (x_rot / a) ** 2 + (y_rot / b) ** 2 <= 1.0
        arr[mask] = 255

        # Analisis komponen
        props = self.engine._extract_grain_properties(mask, np.zeros((h, w, 3), dtype=np.uint8))
        self.assertIsNotNone(props)

        # Toleransi estimasi discretisasi pixel ~ 10%
        expected_L = 2 * a
        expected_W = 2 * b
        self.assertAlmostEqual(props["major_axis_length"], expected_L, delta=5.0)
        self.assertAlmostEqual(props["minor_axis_length"], expected_W, delta=4.0)

    def test_05_empty_black_image(self):
        """Memverifikasi penanganan citra hitam total tanpa butir tidak menghasilkan pembagian nol."""
        empty_img = Image.new("RGB", (300, 300), color=(0, 0, 0))
        res = self.engine.analyze_image(empty_img)

        self.assertEqual(res["grain_count"], 0)
        self.assertEqual(res["butir_kepala"], 0)
        self.assertEqual(res["butir_patah"], 0)
        self.assertEqual(res["butir_menir"], 0)
        self.assertEqual(res["persentase_butir_kepala"], 0.0)

    def test_06_integration_with_quality_engine(self):
        """Memverifikasi hasil CV dapat diumpankan ke quality_engine untuk taksasi harga Bapanas."""
        img = generate_synthetic_rice_image(width=640, height=480, num_grains=60)
        res = self.engine.analyze_image(img)

        eval_res = evaluate_sample(
            sample_id="CV-TEST-BATCH-01",
            kadar_air=13.2,
            butir_patah=res["persentase_butir_patah"],
            butir_menir=res["persentase_butir_menir"],
            benda_asing=res["persentase_benda_asing"],
        )

        self.assertIn("klasifikasi", eval_res)
        self.assertIn("rekomendasi_harga", eval_res)
        self.assertIn(eval_res["klasifikasi"]["kelas_mutu"], ["PREMIUM", "MEDIUM_I", "MEDIUM_II", "SUBSTANDAR"])
        self.assertGreater(eval_res["rekomendasi_harga"]["harga_bersih"], 0)


if __name__ == "__main__":
    unittest.main()
