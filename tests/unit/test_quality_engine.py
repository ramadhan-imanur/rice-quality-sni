#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_quality_engine.py — 20 Skenario Unit Test Kasus Batas
===========================================================

Modul pengujian otomatis untuk quality_engine.py yang mencakup:
- 10 uji klasifikasi kelas mutu (batas ambang SNI 6128:2020)
- 6 uji validasi masukan (penolakan input tak valid)
- 4 uji kalkulasi harga (penalti Bapanas No. 67/2024)

Jalankan: python3 -m pytest code/tests/test_quality_engine.py -v
    atau: python3 -m unittest code.tests.test_quality_engine -v
"""

import sys
import os
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (SRC_DIR, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from quality_engine import (
    validate_input,
    classify_grade,
    calculate_price,
    evaluate_sample,
)


class TestQualityEngine(unittest.TestCase):
    """20 skenario unit test untuk modul quality_engine.py."""

    # ================================================================
    # BAGIAN A: UJI KLASIFIKASI KELAS MUTU (10 test)
    # ================================================================

    def test_01_premium_exact_boundary(self):
        """TC-01: Semua parameter tepat di ambang batas Premium → PREMIUM."""
        result = classify_grade(14.0, 15.0, 0.5, 0.01)
        self.assertEqual(result["kelas_mutu"], "PREMIUM")

    def test_02_premium_ideal(self):
        """TC-02: Beras premium ideal, semua parameter jauh di bawah batas → PREMIUM."""
        result = classify_grade(12.0, 5.0, 0.1, 0.005)
        self.assertEqual(result["kelas_mutu"], "PREMIUM")

    def test_03_medium1_exact_boundary(self):
        """TC-03: Semua parameter tepat di ambang batas Medium I → MEDIUM_I."""
        result = classify_grade(14.0, 20.0, 2.0, 0.02)
        self.assertEqual(result["kelas_mutu"], "MEDIUM_I")

    def test_04_medium1_just_over_premium(self):
        """TC-04: Butir patah sedikit melampaui batas Premium → MEDIUM_I."""
        result = classify_grade(14.0, 15.1, 0.5, 0.01)
        self.assertEqual(result["kelas_mutu"], "MEDIUM_I")

    def test_05_medium2_exact_boundary(self):
        """TC-05: Semua parameter tepat di ambang batas Medium II → MEDIUM_II."""
        result = classify_grade(14.0, 25.0, 5.0, 0.05)
        self.assertEqual(result["kelas_mutu"], "MEDIUM_II")

    def test_06_medium2_just_over_medium1(self):
        """TC-06: Butir patah sedikit melampaui batas Medium I → MEDIUM_II."""
        result = classify_grade(14.0, 20.1, 2.0, 0.02)
        self.assertEqual(result["kelas_mutu"], "MEDIUM_II")

    def test_07_substandar_high_moisture(self):
        """TC-07: Kadar air tinggi (18%) meskipun parameter lain baik → SUBSTANDAR."""
        result = classify_grade(18.0, 10.0, 0.3, 0.005)
        self.assertEqual(result["kelas_mutu"], "SUBSTANDAR")

    def test_08_substandar_high_broken(self):
        """TC-08: Butir patah berlebih (30%) melampaui semua batas → SUBSTANDAR."""
        result = classify_grade(13.0, 30.0, 3.0, 0.03)
        self.assertEqual(result["kelas_mutu"], "SUBSTANDAR")

    def test_09_substandar_excess_foreign(self):
        """TC-09: Benda asing berlebih (0.06%) melampaui Medium II → SUBSTANDAR."""
        result = classify_grade(13.0, 15.0, 0.5, 0.06)
        self.assertEqual(result["kelas_mutu"], "SUBSTANDAR")

    def test_10_substandar_all_bad(self):
        """TC-10: Semua parameter buruk → SUBSTANDAR."""
        result = classify_grade(20.0, 40.0, 10.0, 1.0)
        self.assertEqual(result["kelas_mutu"], "SUBSTANDAR")

    # ================================================================
    # BAGIAN B: UJI VALIDASI MASUKAN (6 test)
    # ================================================================

    def test_11_reject_negative_moisture(self):
        """TC-11: Kadar air negatif harus ditolak → ValueError."""
        with self.assertRaises(ValueError):
            validate_input(-1.0, 10.0, 0.5, 0.01)

    def test_12_reject_excessive_moisture(self):
        """TC-12: Kadar air > 40% (tidak masuk akal) → ValueError."""
        with self.assertRaises(ValueError):
            validate_input(45.0, 10.0, 0.5, 0.01)

    def test_13_reject_string_input(self):
        """TC-13: Masukan huruf alfabet harus ditolak → TypeError."""
        with self.assertRaises(TypeError):
            validate_input("abc", 10.0, 0.5, 0.01)

    def test_14_reject_none_input(self):
        """TC-14: Masukan None harus ditolak → TypeError."""
        with self.assertRaises(TypeError):
            validate_input(None, 10.0, 0.5, 0.01)

    def test_15_reject_negative_broken(self):
        """TC-15: Butir patah negatif harus ditolak → ValueError."""
        with self.assertRaises(ValueError):
            validate_input(13.0, -5.0, 0.5, 0.01)

    def test_16_reject_excessive_foreign(self):
        """TC-16: Benda asing > 10% (batas maks) → ValueError."""
        with self.assertRaises(ValueError):
            validate_input(13.0, 10.0, 0.5, 15.0)

    # ================================================================
    # BAGIAN C: UJI KALKULASI HARGA (4 test)
    # ================================================================

    def test_17_price_premium_no_penalty(self):
        """TC-17: Premium dgn kadar air normal → harga penuh tanpa penalti."""
        result = calculate_price(13.0, "PREMIUM")
        self.assertEqual(result["harga_dasar"], 15_800)
        self.assertEqual(result["penalti_pengeringan"], 0.0)
        self.assertEqual(result["potongan_penyusutan"], 0.0)
        self.assertEqual(result["harga_bersih"], 15_800)

    def test_18_price_moisture_penalty(self):
        """TC-18: Kadar air 16% (kelebihan 2%) → penalti pengeringan + penyusutan."""
        result = calculate_price(16.0, "PREMIUM")
        # Penalti pengeringan: 2 * 150 = 300
        self.assertEqual(result["penalti_pengeringan"], 300.0)
        # Penyusutan: 2 * 0.015 * 15800 = 474
        self.assertEqual(result["potongan_penyusutan"], 474.0)
        # Harga bersih: 15800 - 300 - 474 = 15026
        self.assertEqual(result["harga_bersih"], 15_026.0)

    def test_19_price_substandar_high_moisture(self):
        """TC-19: Substandar dgn kadar air 18% → penalti signifikan."""
        result = calculate_price(18.0, "SUBSTANDAR")
        # Harga dasar Substandar: 11500
        self.assertEqual(result["harga_dasar"], 11_500)
        # Kelebihan: 4%, penalti pengeringan: 4 * 150 = 600
        self.assertEqual(result["penalti_pengeringan"], 600.0)
        # Penyusutan: 4 * 0.015 * 11500 = 690
        self.assertEqual(result["potongan_penyusutan"], 690.0)
        # Harga bersih: 11500 - 600 - 690 = 10210
        self.assertEqual(result["harga_bersih"], 10_210.0)

    def test_20_price_medium_normal(self):
        """TC-20: Medium I dgn kadar air normal → harga penuh tanpa potongan."""
        result = calculate_price(14.0, "MEDIUM_I")
        self.assertEqual(result["harga_dasar"], 13_500)
        self.assertEqual(result["penalti_pengeringan"], 0.0)
        self.assertEqual(result["harga_bersih"], 13_500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
