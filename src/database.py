#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py — Lapisan Persistensi & Jejak Audit SQLite Sistem Sertifikasi Mutu SNI
=================================================================================
Mendukung arsitektur Maker-Checker-Verifier:
1. Akun Pengguna & Hak Akses (Petani, Analis Lab, Admin)
2. Pengajuan Batch Sampel oleh Petani (Status: PENDING)
3. Verifikasi & Penerbitan Sertifikat Mutu Resmi oleh Analis Lab (Status: VERIFIED)
4. Jejak Audit (Audit Trail) komprehensif
5. Tanda Tangan Kriptografi HMAC-SHA256 untuk Integritas Dokumen

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "rice_sni.db")

_env_key = os.environ.get("SNI_SECRET_KEY")
_app_env = os.environ.get("APP_ENV", os.environ.get("NODE_ENV", "development")).lower()

if _env_key:
    SECRET_KEY = _env_key.encode("utf-8")
elif _app_env == "production":
    import logging
    logging.warning("PERINGATAN KEAMANAN: SNI_SECRET_KEY tidak disetel di lingkungan produksi! Menghasilkan kunci acak runtime.")
    SECRET_KEY = secrets.token_bytes(32)
else:
    # Development / testing fallback
    SECRET_KEY = b"UNS_FMIPA_MATEMATIKA_SNI_6128_2020_SECRET_KEY_M0124015"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Membuka koneksi SQLite dengan row_factory dictionary."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash password menggunakan algoritma standar industri PBKDF2-HMAC-SHA256
    dengan 100.000 iterasi dan salt kriptografis acak (CWE-916 Remediation).
    """
    if not salt:
        salt = secrets.token_hex(8)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Memverifikasi kecocokan password dengan hash tersimpan.
    Mendukung verifikasi PBKDF2 dan hash legasi secara aman (constant-time).
    """
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$")
        if len(parts) == 4:
            iterations = int(parts[1])
            salt = parts[2]
            expected_hex = parts[3]
            derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
            return hmac.compare_digest(derived.hex(), expected_hex)
    # Fallback kompatibilitas hash legasi (single SHA-256)
    legacy_salt = "UNS_MAT_SNI_"
    legacy_hash = hashlib.sha256((legacy_salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, stored_hash)


def create_session_token(user_id: int, role: str) -> str:
    """Menghasilkan token sesi bertanda tangan HMAC-SHA256 dengan stempel waktu."""
    ts = int(datetime.now().timestamp())
    msg = f"{user_id}:{role}:{ts}".encode("utf-8")
    sig = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()[:32]
    return f"{user_id}:{role}:{ts}:{sig}"


def verify_session_token(token: str, max_age_seconds: int = 86400) -> Optional[Dict[str, Any]]:
    """Memvalidasi integritas dan masa berlaku token sesi pengguna."""
    if not token or ":" not in token:
        return None
    parts = token.split(":")
    if len(parts) != 4:
        return None
    try:
        user_id = int(parts[0])
        role = parts[1]
        ts = int(parts[2])
        sig = parts[3]
    except (ValueError, TypeError):
        return None

    now_ts = int(datetime.now().timestamp())
    if now_ts - ts > max_age_seconds or ts > now_ts + 300:
        return None

    msg = f"{user_id}:{role}:{ts}".encode("utf-8")
    expected_sig = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected_sig, sig):
        return None

    return {"user_id": user_id, "role": role, "timestamp": ts}



def generate_hmac_signature(
    submission_id: str,
    nik: str,
    kelas_mutu: str,
    tanggal_uji: str,
    harga_bersih: float,
) -> str:
    """
    Menghasilkan tanda tangan digital HMAC-SHA256 dari parameter kunci sertifikat.
    Mencegah pemalsuan angka mutu atau sertifikat rekayasa.
    """
    payload = f"{submission_id}|{nik}|{kelas_mutu}|{tanggal_uji}|{harga_bersih:.2f}"
    sig = hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return sig[:24]  # 24 karakter heksadesimal representasi unik


def verify_hmac_signature(
    submission_id: str,
    nik: str,
    kelas_mutu: str,
    tanggal_uji: str,
    harga_bersih: float,
    signature: str,
) -> bool:
    """Memvalidasi integritas tanda tangan HMAC-SHA256."""
    expected = generate_hmac_signature(
        submission_id, nik, kelas_mutu, tanggal_uji, harga_bersih
    )
    return hmac.compare_digest(expected, signature)


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Menginisialisasi tabel-tabel SQLite dan data benih awal jika belum ada."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # 1. Tabel Users
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nama_lengkap TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('petani', 'analis_lab', 'admin')),
            nik_nip TEXT,
            instansi TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    # 2. Tabel Submissions (Pengajuan Sampel Petani)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            petani_id INTEGER,
            petani_nama TEXT NOT NULL,
            petani_nik TEXT NOT NULL,
            kontak TEXT,
            varietas_padi TEXT NOT NULL,
            asal_lahan TEXT NOT NULL,
            tonase_kg REAL NOT NULL,
            tanggal_panen TEXT NOT NULL,
            catatan TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'VERIFIED', 'REJECTED')),
            barcode_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            verified_at TEXT,
            verified_by INTEGER,
            nomor_sertifikat TEXT,
            FOREIGN KEY (petani_id) REFERENCES users(id),
            FOREIGN KEY (verified_by) REFERENCES users(id)
        );
        """
    )

    # 3. Tabel Certificates (Sertifikat Mutu Resmi)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS certificates (
            nomor_sertifikat TEXT PRIMARY KEY,
            submission_id TEXT NOT NULL UNIQUE,
            analis_id INTEGER NOT NULL,
            analis_nama TEXT NOT NULL,
            analis_nip TEXT NOT NULL,
            analis_instansi TEXT NOT NULL,
            petani_nama TEXT NOT NULL,
            petani_nik TEXT NOT NULL,
            varietas_padi TEXT NOT NULL,
            asal_lahan TEXT NOT NULL,
            tonase_kg REAL NOT NULL,
            tanggal_uji TEXT NOT NULL,
            kadar_air REAL NOT NULL,
            butir_patah REAL NOT NULL,
            butir_menir REAL NOT NULL,
            benda_asing REAL NOT NULL,
            kelas_mutu TEXT NOT NULL,
            label_mutu TEXT NOT NULL,
            harga_dasar REAL NOT NULL,
            penalti_pengeringan REAL NOT NULL,
            potongan_penyusutan REAL NOT NULL,
            harga_bersih REAL NOT NULL,
            signature_hmac TEXT NOT NULL,
            qr_url TEXT NOT NULL,
            pdf_path TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (submission_id) REFERENCES submissions(id),
            FOREIGN KEY (analis_id) REFERENCES users(id)
        );
        """
    )

    # 4. Tabel Audit Logs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            details_json TEXT
        );
        """
    )

    # 5. Indeks Kinerja & Foreign Key Lookups
    cur.execute("CREATE INDEX IF NOT EXISTS idx_submissions_petani_id ON submissions(petani_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_certificates_analis_id ON certificates(analis_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_certificates_petani_nik ON certificates(petani_nik);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_certificates_created_at ON certificates(created_at);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_certificates_signature ON certificates(signature_hmac);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);")

    # Data Benih Awal (Seeding Demo Users)
    demo_users = [
        (
            "petani1",
            hash_password("petani123"),
            "Sutrisno Raharjo",
            "petani",
            "3311012304750001",
            "Gapoktan Sumber Makmur (Sukoharjo)",
            datetime.now().isoformat(),
        ),
        (
            "analis1",
            hash_password("analis123"),
            "Ramadhaan Imanur Rochima",
            "analis_lab",
            "M0124015",
            "Lab Sentral Analisis Mutu FMIPA UNS",
            datetime.now().isoformat(),
        ),
        (
            "admin",
            hash_password("admin123"),
            "Administrator Sistem SNI",
            "admin",
            "199501012024011001",
            "Dinas Pertanian & Ketahanan Pangan",
            datetime.now().isoformat(),
        ),
    ]

    for u in demo_users:
        cur.execute(
            """
            INSERT OR IGNORE INTO users (username, password_hash, nama_lengkap, role, nik_nip, instansi, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            u,
        )

    # Jika tabel submissions masih kosong, masukkan 2 sampel demo (1 PENDING, 1 VERIFIED)
    cur.execute("SELECT COUNT(*) as cnt FROM submissions")
    if cur.fetchone()["cnt"] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_today = datetime.now().strftime("%Y-%m-%d")

        # Sub 1: PENDING
        sub1_id = f"BATCH-{datetime.now().strftime('%Y%m%d')}-001"
        barcode1 = f"SMP-{datetime.now().strftime('%Y%m%d')}-881"
        cur.execute(
            """
            INSERT INTO submissions (
                id, petani_id, petani_nama, petani_nik, kontak,
                varietas_padi, asal_lahan, tonase_kg, tanggal_panen, catatan,
                status, barcode_id, created_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
            """,
            (
                sub1_id,
                "Sutrisno Raharjo",
                "3311012304750001",
                "081234567890",
                "Ciherang Super",
                "Desa Manang, Kec. Grogol, Sukoharjo",
                4500.0,
                date_today,
                "Panen musim rendeng, pengeringan terpal 2 hari",
                barcode1,
                now_str,
            ),
        )

        # Sub 2: VERIFIED
        sub2_id = f"BATCH-{datetime.now().strftime('%Y%m%d')}-002"
        barcode2 = f"SMP-{datetime.now().strftime('%Y%m%d')}-882"
        cert2_id = f"SNI-{datetime.now().strftime('%Y%m%d')}-001"
        cur.execute(
            """
            INSERT INTO submissions (
                id, petani_id, petani_nama, petani_nik, kontak,
                varietas_padi, asal_lahan, tonase_kg, tanggal_panen, catatan,
                status, barcode_id, created_at, verified_at, verified_by, nomor_sertifikat
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, ?, ?, 2, ?)
            """,
            (
                sub2_id,
                "Sutrisno Raharjo",
                "3311012304750001",
                "081234567890",
                "Inpari 32 HDB",
                "Desa Bekonang, Kec. Mojolaban, Sukoharjo",
                6000.0,
                date_today,
                "Beras poles RMU Berkah Mandiri",
                barcode2,
                now_str,
                now_str,
                cert2_id,
            ),
        )

        sig2 = generate_hmac_signature(sub2_id, "3311012304750001", "PREMIUM", now_str, 15800.0)
        qr2_url = f"/verify.html?id={cert2_id}&sig={sig2}"

        cur.execute(
            """
            INSERT INTO certificates (
                nomor_sertifikat, submission_id, analis_id, analis_nama, analis_nip, analis_instansi,
                petani_nama, petani_nik, varietas_padi, asal_lahan, tonase_kg, tanggal_uji,
                kadar_air, butir_patah, butir_menir, benda_asing,
                kelas_mutu, label_mutu, harga_dasar, penalti_pengeringan, potongan_penyusutan,
                harga_bersih, signature_hmac, qr_url, pdf_path, created_at
            ) VALUES (?, ?, 2, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cert2_id,
                sub2_id,
                "Ramadhaan Imanur Rochima",
                "M0124015",
                "Lab Sentral Analisis Mutu FMIPA UNS",
                "Sutrisno Raharjo",
                "3311012304750001",
                "Inpari 32 HDB",
                "Desa Bekonang, Kec. Mojolaban, Sukoharjo",
                6000.0,
                now_str,
                13.4,
                12.5,
                0.3,
                0.008,
                "PREMIUM",
                "Premium",
                15800.0,
                0.0,
                0.0,
                15800.0,
                sig2,
                qr2_url,
                f"output/sertifikat_{cert2_id}.pdf",
                now_str,
            ),
        )

    conn.commit()
    conn.close()


def log_audit(
    action: str,
    entity_type: str,
    entity_id: str,
    details: Dict[str, Any],
    user_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Mencatat aktivitas ke dalam tabel audit_logs."""
    conn = get_db_connection(db_path)
    conn.execute(
        """
        INSERT INTO audit_logs (timestamp, user_id, action, entity_type, entity_id, details_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            user_id,
            action,
            entity_type,
            entity_id,
            json.dumps(details, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DEFAULT_DB_PATH)
