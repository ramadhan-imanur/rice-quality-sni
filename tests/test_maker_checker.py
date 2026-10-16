#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_maker_checker.py — Pengujian Otomatis Arsitektur Maker-Checker & Anti-Fraud
================================================================================
Menguji:
1. Integritas Skema SQLite & Seeding Akun Pengguna
2. Pembuatan & Validasi Tanda Tangan Digital Kriptografi HMAC-SHA256
3. Deteksi Pemalsuan / Modifikasi Ilegal (Tamper Detection)
4. Alur Kerja Maker (Petani buat batch -> PENDING -> Label Terbit)
5. Alur Kerja Checker (Analis uji lab -> VERIFIED -> Sertifikat CoA Terbit)
6. Generator QR Code ISO 18004 Vektor Tanpa Library Luar
7. Watermark Otomatis pada Sertifikat Tak Terverifikasi
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import (
    init_db,
    get_db_connection,
    hash_password,
    generate_hmac_signature,
    verify_hmac_signature,
    log_audit,
)
from quality_engine import evaluate_sample
from pdf_generator import generate_certificate, generate_sample_label
from qr_codec import generate_qr_matrix


class TestMakerCheckerAntiFraud(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)
        self.output_dir = tempfile.mkdtemp()

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_01_db_seeding_users(self):
        """Memverifikasi akun pengguna demo berhasil diinisialisasi."""
        conn = get_db_connection(self.temp_db_path)
        cur = conn.cursor()
        cur.execute("SELECT username, role FROM users")
        users = {r["username"]: r["role"] for r in cur.fetchall()}
        conn.close()

        self.assertIn("petani1", users)
        self.assertEqual(users["petani1"], "petani")
        self.assertIn("analis1", users)
        self.assertEqual(users["analis1"], "analis_lab")
        self.assertIn("admin", users)

    def test_02_hmac_signature_integrity(self):
        """Memverifikasi signature HMAC-SHA256 valid dan mendeteksi tampering."""
        sub_id = "BATCH-20261016-001"
        nik = "3311012304750001"
        kelas = "PREMIUM"
        tgl = "16-10-2026 14:00 WIB"
        harga = 15800.0

        sig = generate_hmac_signature(sub_id, nik, kelas, tgl, harga)
        self.assertTrue(len(sig) >= 16)

        # 1. Verifikasi tanda tangan asli
        is_valid = verify_hmac_signature(sub_id, nik, kelas, tgl, harga, sig)
        self.assertTrue(is_valid)

        # 2. Deteksi pemalsuan angka harga
        is_tampered_price = verify_hmac_signature(sub_id, nik, kelas, tgl, 17500.0, sig)
        self.assertFalse(is_tampered_price)

        # 3. Deteksi pemalsuan kelas mutu (misal dari Medium dinaikkan jadi Premium)
        is_tampered_grade = verify_hmac_signature(sub_id, nik, "MEDIUM_I", tgl, harga, sig)
        self.assertFalse(is_tampered_grade)

        # 4. Deteksi pemalsuan NIK petani
        is_tampered_nik = verify_hmac_signature(sub_id, "3311099999990001", kelas, tgl, harga, sig)
        self.assertFalse(is_tampered_nik)

    def test_03_maker_submission_workflow(self):
        """Petani mengajukan batch sampel dan menghasilkan label pengantar ber-barcode."""
        conn = get_db_connection(self.temp_db_path)
        cur = conn.cursor()
        sub_id = "BATCH-TEST-001"
        barcode_id = "SMP-TEST-001"

        cur.execute(
            """
            INSERT INTO submissions (
                id, petani_id, petani_nama, petani_nik, kontak,
                varietas_padi, asal_lahan, tonase_kg, tanggal_panen, catatan,
                status, barcode_id, created_at
            ) VALUES (?, 1, 'Budi Santoso', '3311019999990001', '08123456789',
                      'Inpari 32', 'Mojolaban', 5000, '2026-10-14', 'Beras sawah',
                      'PENDING', ?, '2026-10-16 10:00:00')
            """,
            (sub_id, barcode_id),
        )
        conn.commit()

        # Pastikan status awal adalah PENDING
        cur.execute("SELECT status FROM submissions WHERE id = ?", (sub_id,))
        status = cur.fetchone()["status"]
        self.assertEqual(status, "PENDING")
        conn.close()

        # Buat label pengantar PDF
        sub_dict = {
            "id": sub_id,
            "barcode_id": barcode_id,
            "petani_nama": "Budi Santoso",
            "petani_nik": "3311019999990001",
            "varietas_padi": "Inpari 32",
            "asal_lahan": "Mojolaban",
            "tonase_kg": 5000.0,
            "tanggal_panen": "2026-10-14",
            "catatan": "Sampel 1 kg",
        }
        label_path = generate_sample_label(sub_dict, output_dir=self.output_dir)
        self.assertTrue(os.path.exists(label_path))
        self.assertGreater(os.path.getsize(label_path), 5000)

    def test_04_checker_verification_and_certificate(self):
        """Analis lab menguji parameter, menerbitkan sertifikat CoA resmi berstempel QR."""
        eval_res = evaluate_sample(13.2, 12.0, 0.3, 0.008, sample_id="SAMPEL-LAB-01")
        self.assertEqual(eval_res["klasifikasi"]["kelas_mutu"], "PREMIUM")

        pdf_path = generate_certificate(
            eval_res,
            output_dir=self.output_dir,
            is_verified=True,
            petani_info={
                "petani_nama": "Budi Santoso",
                "petani_nik": "3311019999990001",
                "varietas_padi": "Inpari 32",
                "asal_lahan": "Mojolaban",
                "tonase_kg": 5000.0,
            },
            analis_info={
                "analis_nama": "Ramadhaan Imanur Rochima",
                "analis_nip": "M0124015",
                "analis_instansi": "Lab Sentral Analisis Mutu FMIPA UNS",
            },
        )
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 10000)

    def test_05_unverified_simulation_watermark(self):
        """Sertifikat draft simulasi mandiri harus memuat watermark peringatan."""
        eval_res = evaluate_sample(15.5, 22.0, 2.5, 0.03, sample_id="SIMULASI-TEST")
        pdf_path = generate_certificate(
            eval_res,
            output_dir=self.output_dir,
            is_verified=False,  # Unverified simulation
        )
        self.assertTrue(os.path.exists(pdf_path))

        with open(pdf_path, "rb") as f:
            content = f.read()
        # Periksa keberadaan watermark di stream PDF
        self.assertIn(b"SIMULASI MANDIRI - BUKAN BUKTI MUTU SAH", content)

    def test_06_pure_python_qr_code(self):
        """QR Code generator menghasilkan matriks valid untuk verifikasi URL."""
        test_url = "http://localhost:8000/verify.html?id=SNI-20261016-001&sig=A8F9D2E4C0B1"
        matrix = generate_qr_matrix(test_url, "L")
        self.assertIsInstance(matrix, list)
        self.assertGreater(len(matrix), 20)
        self.assertEqual(len(matrix), len(matrix[0]))
        # Finder pattern modul pojok kiri atas harus hitam
        self.assertTrue(matrix[0][0])
        self.assertTrue(matrix[0][6])
        self.assertTrue(matrix[6][0])


if __name__ == "__main__":
    unittest.main()
