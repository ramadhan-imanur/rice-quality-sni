#!/usr/bin/env python3
# ==============================================================================
# test_security_hardened.py — Automated Security & OWASP Top 10 Hardening Tests
# Sistem Taksasi Mutu Beras SNI 6128:2020 & Anti-Fraud Engine
# ==============================================================================

import io
import os
import sys
import time
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database import (
    create_session_token,
    generate_hmac_signature,
    hash_password,
    verify_hmac_signature,
    verify_password,
    verify_session_token,
)
from src.api_server import (
    InMemoryRateLimiter,
    MAX_PAYLOAD_SIZE,
    RiceQualityAPIHandler,
    _is_safe_id,
    _mask_nik,
)


class TestSecurityHardening(unittest.TestCase):
    """Pengujian Unit Keamanan Aplikasi (OWASP Top 10, CWE-400, CWE-770, CWE-22, CWE-359)."""

    def test_01_rate_limiter_sliding_window(self):
        """Memverifikasi ketahanan pembatasan laju permintaan (CWE-770 Rate Limiter)."""
        limiter = InMemoryRateLimiter()
        client_key = "192.168.1.100"

        # Kirim 5 permintaan dengan batas 5 per jendela 2 detik
        for _ in range(5):
            self.assertTrue(limiter.is_allowed(client_key, max_requests=5, window_seconds=2))

        # Permintaan ke-6 harus langsung ditolak
        self.assertFalse(limiter.is_allowed(client_key, max_requests=5, window_seconds=2))

        # Klien lain dengan IP berbeda harus tetap diizinkan
        self.assertTrue(limiter.is_allowed("192.168.1.101", max_requests=5, window_seconds=2))

    def test_02_path_traversal_defense(self):
        """Memverifikasi pencegahan injeksi direktori / Path Traversal (CWE-22)."""
        self.assertTrue(_is_safe_id("BATCH-20261016-ABCD"))
        self.assertTrue(_is_safe_id("TKS-20261016-123456"))

        # Upaya traversal direktori harus ditolak
        self.assertFalse(_is_safe_id("../etc/passwd"))
        self.assertFalse(_is_safe_id("..\\windows\\system32"))
        self.assertFalse(_is_safe_id("/root/.ssh/id_rsa"))
        self.assertFalse(_is_safe_id("batch;rm -rf /"))
        self.assertFalse(_is_safe_id(""))

    def test_03_pii_masking_privacy(self):
        """Memverifikasi penyamaran data pribadi NIK sesuai UU PDP No. 27/2022 (CWE-359)."""
        nik_asli = "3311012304750001"
        nik_masked = _mask_nik(nik_asli)

        self.assertEqual(len(nik_masked), 16)
        self.assertTrue(nik_masked.startswith("331101"))
        self.assertTrue(nik_masked.endswith("0001"))
        self.assertIn("******", nik_masked)
        self.assertNotEqual(nik_asli, nik_masked)

        # Kasus nilai None atau tidak valid
        self.assertEqual(_mask_nik(None), "****")
        self.assertEqual(_mask_nik("123"), "****")

    def test_04_session_token_integrity_and_expiry(self):
        """Memverifikasi keamanan token sesi HMAC-SHA256 & mitigasi manipulasi role."""
        user_id = 42
        role = "analis_lab"
        token = create_session_token(user_id, role)

        # 1. Validasi token asli
        verified = verify_session_token(token)
        self.assertIsNotNone(verified)
        self.assertEqual(verified["user_id"], user_id)
        self.assertEqual(verified["role"], role)

        # 2. Upaya eskalasi wewenang (Privilege Escalation Tampering)
        parts = token.split(":")
        tampered_token = f"{parts[0]}:admin:{parts[2]}:{parts[3]}"
        self.assertIsNone(verify_session_token(tampered_token))

        # 3. Token kadaluwarsa
        expired_token = f"{user_id}:{role}:{int(time.time() - 90000)}:{parts[3]}"
        self.assertIsNone(verify_session_token(expired_token, max_age_seconds=86400))

    def test_05_hmac_tamper_detection(self):
        """Memverifikasi deteksi pemalsuan angka taksasi pada tanda tangan digital (CWE-347)."""
        sub_id = "BATCH-001"
        nik = "3311012304750001"
        kelas = "PREMIUM"
        tgl = "2026-10-16"
        harga = 15800.0

        sig = generate_hmac_signature(sub_id, nik, kelas, tgl, harga)
        self.assertTrue(verify_hmac_signature(sub_id, nik, kelas, tgl, harga, sig))

        # Coba manipulasi harga dari 15.800 menjadi 16.000
        self.assertFalse(verify_hmac_signature(sub_id, nik, kelas, tgl, 16000.0, sig))

        # Coba manipulasi kelas mutu dari PREMIUM menjadi MEDIUM_I
        self.assertFalse(verify_hmac_signature(sub_id, nik, "MEDIUM_I", tgl, harga, sig))

        # Coba manipulasi NIK pemilik
        self.assertFalse(verify_hmac_signature(sub_id, "3311019999999999", kelas, tgl, harga, sig))

    def test_06_dos_payload_limit_constant(self):
        """Memverifikasi batas payload maksimum 15MB untuk proteksi DoS Buffer Exhaustion (CWE-400)."""
        self.assertEqual(MAX_PAYLOAD_SIZE, 15 * 1024 * 1024)

    def test_07_password_hashing_pbkdf2(self):
        """Memverifikasi penyimpanan kata sandi ter-hash dengan salt unik (CWE-256)."""
        pwd = "SandiRahasia2026!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)

        # Salt unik menghasilkan hash berbeda untuk kata sandi yang sama
        self.assertNotEqual(h1, h2)
        self.assertTrue(h1.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password(pwd, h1))
        self.assertTrue(verify_password(pwd, h2))
        self.assertFalse(verify_password("PasswordSalah", h1))

    def test_08_cv_engine_decompression_bomb_guard(self):
        """Memverifikasi batas piksel dekompresi Pillow (CWE-400 / Decompression Bomb Guard)."""
        from PIL import Image
        from src.cv_engine import analyze_rice_image
        self.assertLessEqual(Image.MAX_IMAGE_PIXELS, 25_000_000)

    def test_09_database_security_pragmas(self):
        """Memverifikasi penegakan PRAGMA foreign_keys dan secure_delete pada koneksi SQLite."""
        import tempfile
        from src.database import get_db_connection
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            conn = get_db_connection(tmp.name)
            fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            sd = conn.execute("PRAGMA secure_delete;").fetchone()[0]
            conn.close()
            self.assertEqual(fk, 1)
            self.assertEqual(sd, 1)


if __name__ == "__main__":
    unittest.main()
