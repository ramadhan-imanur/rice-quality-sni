#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api_server.py — Peladen REST API & Backend Sistem Sertifikasi Mutu Beras SNI
=============================================================================
Menjembatani antarmuka Web dengan modul Python:
1. Otentikasi Peran (Petani, Analis Lab, Admin)
2. Maker Workflow: Pengajuan batch sampel petani (Status PENDING) & Cetak Label Sampel
3. Checker Workflow: Pengujian lab terkalibrasi, klasifikasi deterministik O(1)
4. Verifier Workflow: Penerbitan sertifikat digital berstempel HMAC-SHA256 & QR Code
5. Endpoint Verifikasi Publik Anti-Fraud: /api/verify & /verify.html
6. Penyajian Berkas Statis Web (HTML, CSS, JS)

100% Menggunakan Pustaka Standar Python (http.server, sqlite3, json, hmac).
Nol dependensi eksternal — Siap dijalankan di komputer luring manapun.

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import base64
import http.server
import json
import mimetypes
import os
import re
import socketserver
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from cv_engine import analyze_rice_image, generate_synthetic_rice_image
from database import (
    DEFAULT_DB_PATH,
    create_session_token,
    generate_hmac_signature,
    get_db_connection,
    hash_password,
    init_db,
    log_audit,
    verify_hmac_signature,
    verify_password,
    verify_session_token,
)
from pdf_generator import generate_certificate, generate_sample_label
from quality_engine import (
    HARGA_ACUAN,
    KELAS_MUTU,
    KELAS_SUBSTANDAR,
    evaluate_sample,
    validate_input,
)

PORT = int(os.environ.get("PORT", 8000))
WEB_DIR = os.path.join(CURRENT_DIR, "web")
OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")


def _is_safe_id(id_str: str) -> bool:
    """Validasi format ID agar terhindar dari injeksi direktori / path traversal."""
    return bool(id_str and re.match(r"^[A-Za-z0-9\-_]+$", id_str))


def _mask_nik(nik: Optional[str]) -> str:
    """Masking 16-digit NIK petani untuk pelindungan data pribadi (UU PDP No. 27/2022)."""
    if not nik or len(nik) < 10:
        return "****"
    return f"{nik[:6]}******{nik[-4:]}"


class RiceQualityAPIHandler(http.server.SimpleHTTPRequestHandler):
    """Handler HTTP kustom untuk API RESTful dan berkas statis web."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def _apply_security_headers(self) -> None:
        """Menerapkan tajuk keamanan web standar (Defense-in-Depth)."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:;",
        )

    def _get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Mengekstrak dan memverifikasi token sesi dari header Authorization atau X-Session-Token."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "X-Session-Token" in self.headers:
            token = self.headers.get("X-Session-Token", "").strip()

        if not token:
            return None
        return verify_session_token(token)

    def _send_json(self, data: Any, status_code: int = 200) -> None:
        """Mengirimkan balasan JSON berformat rapi dengan tajuk keamanan."""
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Session-Token")
        self._apply_security_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_json(self, message: str, status_code: int = 400) -> None:
        """Mengirimkan balasan galat JSON standar."""
        self._send_json({"success": False, "error": message}, status_code=status_code)

    def _send_file(self, file_path: str, content_type: str = "application/pdf") -> None:
        """Mengirimkan berkas biner (misal PDF) ke peramban dengan tajuk keamanan."""
        if not os.path.isfile(file_path):
            self._send_error_json("Berkas tidak ditemukan di server", 404)
            return

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self._apply_security_headers()
        self.end_headers()

        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

    def _parse_json_body(self) -> Dict[str, Any]:
        """Membaca dan mem-parsing isi tubuh permintaan HTTP bertipe JSON."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise ValueError("Bad JSON payload")

    def do_OPTIONS(self) -> None:
        """Menangani pre-flight CORS."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # =========================================================================
    # PENANGAN GET
    # =========================================================================
    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API: Cek Keaslian Sertifikat (Public Anti-Fraud Verification)
        if path == "/api/verify":
            cert_id = query.get("id", [""])[0].strip()
            sig = query.get("sig", [""])[0].strip()

            if not cert_id:
                self._send_error_json("Parameter nomor sertifikat ('id') wajib disertakan.", 400)
                return

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM certificates WHERE nomor_sertifikat = ?", (cert_id,))
            row = cur.fetchone()
            conn.close()

            if not row:
                log_audit("VERIFY_PUBLIC_NOT_FOUND", "CERTIFICATE", cert_id, {"query_sig": sig})
                self._send_json({
                    "valid": False,
                    "status": "NOT_FOUND",
                    "badge": "TIDAK TERDAFTAR",
                    "message": f"Sertifikat nomor '{cert_id}' tidak ditemukan dalam database resmi laboratorium.",
                }, 404)
                return

            cert_data = dict(row)
            # Masking NIK untuk publik
            user = self._get_authenticated_user()
            if not user or user["role"] not in ("analis_lab", "admin"):
                cert_data["petani_nik"] = _mask_nik(cert_data.get("petani_nik"))

            # Validasi Tanda Tangan Kriptografi
            stored_sig = cert_data["signature_hmac"]
            expected_sig = generate_hmac_signature(
                row["submission_id"],
                row["petani_nik"],
                row["kelas_mutu"],
                row["tanggal_uji"],
                row["harga_bersih"],
            )

            is_tampered = False
            if sig and not verify_hmac_signature(
                row["submission_id"],
                row["petani_nik"],
                row["kelas_mutu"],
                row["tanggal_uji"],
                row["harga_bersih"],
                sig,
            ):
                is_tampered = True

            if is_tampered:
                log_audit("VERIFY_TAMPER_ALERT", "CERTIFICATE", cert_id, {"input_sig": sig, "stored_sig": stored_sig})
                self._send_json({
                    "valid": False,
                    "status": "TAMPERED",
                    "badge": "PERINGATAN PEMALSUAN",
                    "message": "Peringatan keras! Tanda tangan digital tidak sesuai dengan arsip server. Angka taksasi kemungkinan telah dimodifikasi secara ilegal!",
                    "certificate": cert_data,
                }, 200)
                return

            log_audit("VERIFY_PUBLIC_SUCCESS", "CERTIFICATE", cert_id, {"verified": True})
            self._send_json({
                "valid": True,
                "status": "VERIFIED_OFFICIAL",
                "badge": "TERVERIFIKASI SAH",
                "message": "Lembar taksasi ini sah, asli, dan tercatat resmi dalam Basis Data Uji Mutu SNI 6128:2020.",
                "certificate": cert_data,
            }, 200)
            return

        # 2. API: Daftar Pengajuan Sampel (Submissions)
        if path == "/api/submissions":
            status_filter = query.get("status", [None])[0]
            conn = get_db_connection()
            cur = conn.cursor()
            if status_filter:
                cur.execute("SELECT * FROM submissions WHERE status = ? ORDER BY created_at DESC", (status_filter,))
            else:
                cur.execute("SELECT * FROM submissions ORDER BY created_at DESC")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            # Privasi & Pelindungan Data Pribadi (UU PDP): Masking PII jika belum terotentikasi
            user = self._get_authenticated_user()
            if not user or user["role"] not in ("analis_lab", "admin"):
                for r in rows:
                    r["petani_nik"] = _mask_nik(r.get("petani_nik"))
                    if r.get("kontak"):
                        k = r["kontak"]
                        r["kontak"] = f"{k[:4]}****{k[-3:]}" if len(k) > 7 else "****"

            self._send_json({"success": True, "count": len(rows), "submissions": rows})
            return

        # 3. API: Detail Pengajuan Tertentu
        if path.startswith("/api/submissions/") and not path.endswith("/label"):
            sub_id = path.split("/")[3]
            if not _is_safe_id(sub_id):
                self._send_error_json("Format ID pengajuan tidak valid.", 400)
                return

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                self._send_error_json("Pengajuan tidak ditemukan", 404)
                return

            sub_dict = dict(row)
            user = self._get_authenticated_user()
            if not user or (user["role"] not in ("analis_lab", "admin") and user.get("user_id") != sub_dict.get("petani_id")):
                sub_dict["petani_nik"] = _mask_nik(sub_dict.get("petani_nik"))
                if sub_dict.get("kontak"):
                    k = sub_dict["kontak"]
                    sub_dict["kontak"] = f"{k[:4]}****{k[-3:]}" if len(k) > 7 else "****"

            self._send_json({"success": True, "submission": sub_dict})
            return

        # 4. API: Unduh Label Pengantar Sampel PDF
        if path.startswith("/api/submissions/") and path.endswith("/label"):
            sub_id = path.split("/")[3]
            if not _is_safe_id(sub_id):
                self._send_error_json("Format ID pengajuan tidak valid.", 400)
                return

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                self._send_error_json("Pengajuan tidak ditemukan", 404)
                return
            sub_data = dict(row)
            # Buat berkas label jika belum ada
            label_path = os.path.join(OUTPUT_DIR, f"label_{sub_id.replace('/', '-')}.pdf")
            if not os.path.exists(label_path):
                label_path = generate_sample_label(sub_data, output_dir=OUTPUT_DIR)
            self._send_file(label_path)
            return

        # 5. API: Daftar Sertifikat Terbit
        if path == "/api/certificates":
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM certificates ORDER BY created_at DESC")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            # Privasi & Pelindungan Data Pribadi (UU PDP): Masking PII jika belum terotentikasi
            user = self._get_authenticated_user()
            if not user or user["role"] not in ("analis_lab", "admin"):
                for r in rows:
                    r["petani_nik"] = _mask_nik(r.get("petani_nik"))

            self._send_json({"success": True, "count": len(rows), "certificates": rows})
            return

        # 6. API: Unduh Berkas Sertifikat PDF
        if path.startswith("/api/certificates/") and path.endswith("/download"):
            cert_id = path.split("/")[3]
            if not _is_safe_id(cert_id):
                self._send_error_json("Format nomor taksasi tidak valid.", 400)
                return
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM certificates WHERE nomor_sertifikat = ?", (cert_id,))
            row = cur.fetchone()
            conn.close()
            if not row:
                self._send_error_json("Sertifikat tidak ditemukan", 404)
                return
            cert_data = dict(row)
            pdf_path = cert_data.get("pdf_path")
            safe_id = cert_id.replace("/", "-")
            if not pdf_path or not os.path.exists(pdf_path):
                alt1 = os.path.join(OUTPUT_DIR, f"taksasi_{safe_id}.pdf")
                alt2 = os.path.join(OUTPUT_DIR, f"sertifikat_{safe_id}.pdf")
                if os.path.exists(alt1):
                    pdf_path = alt1
                elif os.path.exists(alt2):
                    pdf_path = alt2
            if not pdf_path or not os.path.exists(pdf_path):
                # Regenerasi dokumen taksasi jika berkas fisik hilang
                eval_res = {
                    "nomor_sertifikat": cert_data["nomor_sertifikat"],
                    "sample_id": cert_data["submission_id"],
                    "tanggal_uji": cert_data["tanggal_uji"],
                    "parameter_uji": {
                        "kadar_air": cert_data["kadar_air"],
                        "butir_patah": cert_data["butir_patah"],
                        "butir_menir": cert_data["butir_menir"],
                        "benda_asing": cert_data["benda_asing"],
                    },
                    "klasifikasi": {
                        "kelas_mutu": cert_data["kelas_mutu"],
                        "label_mutu": cert_data["label_mutu"],
                    },
                    "rekomendasi_harga": {
                        "harga_dasar": cert_data["harga_dasar"],
                        "penalti_pengeringan": cert_data["penalti_pengeringan"],
                        "potongan_penyusutan": cert_data["potongan_penyusutan"],
                        "harga_bersih": cert_data["harga_bersih"],
                    },
                }
                pdf_path = generate_certificate(
                    eval_res,
                    output_dir=OUTPUT_DIR,
                    is_verified=True,
                    petani_info={
                        "petani_nama": cert_data["petani_nama"],
                        "petani_nik": cert_data["petani_nik"],
                        "varietas_padi": cert_data["varietas_padi"],
                        "asal_lahan": cert_data["asal_lahan"],
                        "tonase_kg": cert_data["tonase_kg"],
                    },
                    analis_info={
                        "analis_nama": cert_data["analis_nama"],
                        "analis_nip": cert_data["analis_nip"],
                        "analis_instansi": cert_data["analis_instansi"],
                    },
                    signature_hmac=cert_data["signature_hmac"],
                    qr_url=cert_data["qr_url"],
                )
            self._send_file(pdf_path)
            return

        # 7. API: Ringkasan Statistik Sistem
        if path == "/api/stats":
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as total FROM submissions")
            tot_sub = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) as pending FROM submissions WHERE status = 'PENDING'")
            tot_pend = cur.fetchone()["pending"]
            cur.execute("SELECT COUNT(*) as verified FROM submissions WHERE status = 'VERIFIED'")
            tot_ver = cur.fetchone()["verified"]
            cur.execute("SELECT SUM(tonase_kg) as tonase FROM submissions")
            tot_ton = cur.fetchone()["tonase"] or 0.0

            cur.execute("SELECT kelas_mutu, COUNT(*) as cnt FROM certificates GROUP BY kelas_mutu")
            breakdown = {r["kelas_mutu"]: r["cnt"] for r in cur.fetchall()}
            conn.close()

            self._send_json({
                "success": True,
                "stats": {
                    "total_submissions": tot_sub,
                    "pending_submissions": tot_pend,
                    "verified_submissions": tot_ver,
                    "total_tonase_kg": tot_ton,
                    "breakdown": breakdown,
                }
            })
            return

        # Default fallback: Layani berkas statis web (index.html, style.css, app.js, verify.html)
        super().do_GET()

    # =========================================================================
    # PENANGAN POST
    # =========================================================================
    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            body = self._parse_json_body()
        except ValueError:
            self._send_error_json("Payload JSON tidak valid", 400)
            return

        # 1. API: Otentikasi Masuk Pengguna
        if path == "/api/auth/login":
            username = body.get("username", "").strip()
            password = body.get("password", "")
            if not username or not password:
                self._send_error_json("Username dan password wajib diisi.", 400)
                return

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, username, password_hash, nama_lengkap, role, nik_nip, instansi FROM users WHERE username = ?", (username,))
            user = cur.fetchone()
            conn.close()

            if not user or not verify_password(password, user["password_hash"]):
                self._send_error_json("Kredensial login salah. Silakan coba akun demo: petani1 / analis1 / admin (password: petani123 / analis123 / admin123)", 401)
                return

            u_dict = dict(user)
            u_dict.pop("password_hash", None)
            token = create_session_token(u_dict["id"], u_dict["role"])
            log_audit("USER_LOGIN", "USER", str(u_dict["id"]), {"username": username}, user_id=u_dict["id"])
            self._send_json({"success": True, "user": u_dict, "token": token})
            return

        # 2. API: Simulasi Mandiri (Kalkulator Petani - Tanpa Sertifikat Resmi)
        if path == "/api/simulate":
            try:
                ka = float(body.get("kadar_air", 0.0))
                bp = float(body.get("butir_patah", 0.0))
                mn = float(body.get("butir_menir", 0.0))
                ba = float(body.get("benda_asing", 0.0))
                sample_name = body.get("sample_id", "Simulasi Mandiri")
            except (ValueError, TypeError):
                self._send_error_json("Masukan 4 parameter harus berupa angka valid.", 400)
                return

            try:
                eval_res = evaluate_sample(ka, bp, mn, ba, sample_id=sample_name)
            except (ValueError, TypeError) as e:
                self._send_error_json(str(e), 400)
                return

            # Tambahkan analisis traffic light indikator
            indicators = {}
            for param, val, p_max, m1_max, m2_max in [
                ("kadar_air", ka, 14.0, 14.0, 14.0),
                ("butir_patah", bp, 15.0, 20.0, 25.0),
                ("butir_menir", mn, 0.50, 2.00, 5.00),
                ("benda_asing", ba, 0.01, 0.02, 0.05),
            ]:
                if val <= p_max:
                    color = "green"
                    status_text = "Memenuhi Standar Premium"
                elif val <= m1_max:
                    color = "blue"
                    status_text = "Masuk Batas Toleransi Medium I"
                elif val <= m2_max:
                    color = "amber"
                    status_text = "Masuk Batas Toleransi Medium II"
                else:
                    color = "red"
                    status_text = "Melampaui Toleransi (Substandar)"
                indicators[param] = {"value": val, "color": color, "status_text": status_text}

            eval_res["indicators"] = indicators
            eval_res["is_simulation"] = True
            eval_res["watermark_notice"] = "SIMULASI PRELIMINER MANDIRI — BUKAN BUKTI MUTU RESMI LABORATORIUM"

            self._send_json({"success": True, "result": eval_res})
            return

        # 2b. API: Analisis Citra Beras (Computer Vision)
        if path == "/api/cv/analyze":
            img_b64 = body.get("image_base64", "")
            use_demo = body.get("demo", False)
            ka = float(body.get("kadar_air", 13.5))

            if use_demo or not img_b64:
                synth_img = generate_synthetic_rice_image()
                cv_res = analyze_rice_image(synth_img)
            else:
                if "," in img_b64:
                    img_b64 = img_b64.split(",", 1)[1]
                try:
                    raw_bytes = base64.b64decode(img_b64)
                    cv_res = analyze_rice_image(raw_bytes)
                except Exception as e:
                    self._send_error_json(f"Gagal memproses berkas citra: {str(e)}", 400)
                    return

            if not cv_res.get("success", False):
                self._send_error_json(cv_res.get("error", "Gagal mendeteksi butiran beras."), 400)
                return

            p = cv_res["parameter_terukur"]
            bp = p["butir_patah_pct"]
            mn = p["butir_menir_pct"]
            ba = p["benda_asing_pct"]

            eval_res = evaluate_sample(ka, bp, mn, ba, sample_id=body.get("sample_id", "Taksasi-Foto-CV"))

            # Indikator warna
            indicators = {}
            for param, val, p_max, m1_max, m2_max in [
                ("kadar_air", ka, 14.0, 14.0, 14.0),
                ("butir_patah", bp, 15.0, 20.0, 25.0),
                ("butir_menir", mn, 0.50, 2.00, 5.00),
                ("benda_asing", ba, 0.01, 0.02, 0.05),
            ]:
                if val <= p_max:
                    color = "green"
                    status_text = "Memenuhi Standar Premium"
                elif val <= m1_max:
                    color = "blue"
                    status_text = "Masuk Batas Toleransi Medium I"
                elif val <= m2_max:
                    color = "amber"
                    status_text = "Masuk Batas Toleransi Medium II"
                else:
                    color = "red"
                    status_text = "Melampaui Toleransi (Substandar)"
                indicators[param] = {"value": val, "color": color, "status_text": status_text}

            eval_res["indicators"] = indicators

            self._send_json({
                "success": True,
                "cv_metrics": cv_res,
                "measurements": {
                    "grain_count": cv_res.get("total_grains", 0),
                    "persentase_butir_kepala": p.get("butir_kepala_pct", 0.0),
                    "persentase_butir_patah": bp,
                    "persentase_butir_menir": mn,
                    "persentase_benda_asing": ba,
                    "reference_L0_px": cv_res.get("l0_reference_px", 0.0),
                },
                "annotated_image_base64": cv_res.get("annotated_image_base64", ""),
                "evaluation": eval_res,
            })
            return

        # 3. API: Petani Mengajukan Sampel Batch (Maker)
        if path == "/api/submissions":
            petani_id = body.get("petani_id", 1)
            petani_nama = body.get("petani_nama", "").strip()
            petani_nik = body.get("petani_nik", "").strip()
            kontak = body.get("kontak", "").strip()
            varietas = body.get("varietas_padi", "").strip()
            asal_lahan = body.get("asal_lahan", "").strip()
            tonase = float(body.get("tonase_kg", 0.0))
            tgl_panen = body.get("tanggal_panen", "").strip()
            catatan = body.get("catatan", "").strip()

            if not petani_nama or not petani_nik or not varietas or not asal_lahan or tonase <= 0:
                self._send_error_json("Semua kolom identitas batch (Nama, NIK, Varietas, Asal Lahan, Tonase) wajib diisi lengkap.", 400)
                return

            now = datetime.now()
            sub_id = f"BATCH-{now.strftime('%Y%m%d')}-{os.urandom(2).hex().upper()}"
            barcode_id = f"SMP-{now.strftime('%Y%m%d')}-{os.urandom(2).hex().upper()}"
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO submissions (
                    id, petani_id, petani_nama, petani_nik, kontak,
                    varietas_padi, asal_lahan, tonase_kg, tanggal_panen, catatan,
                    status, barcode_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                """,
                (
                    sub_id, petani_id, petani_nama, petani_nik, kontak,
                    varietas, asal_lahan, tonase, tgl_panen, catatan,
                    barcode_id, now_str,
                )
            )
            conn.commit()
            conn.close()

            # Generate Label Sampel PDF
            sub_dict = {
                "id": sub_id,
                "barcode_id": barcode_id,
                "petani_nama": petani_nama,
                "petani_nik": petani_nik,
                "kontak": kontak,
                "varietas_padi": varietas,
                "asal_lahan": asal_lahan,
                "tonase_kg": tonase,
                "tanggal_panen": tgl_panen,
                "catatan": catatan,
            }
            label_pdf_path = generate_sample_label(sub_dict, output_dir=OUTPUT_DIR)

            log_audit("SUBMIT_SAMPLE_BATCH", "SUBMISSION", sub_id, sub_dict, user_id=petani_id)

            self._send_json({
                "success": True,
                "message": "Pengajuan batch sampel berhasil dibuat! Silakan unduh dan cetak Label Pengantar Sampel.",
                "submission": sub_dict,
                "label_url": f"/api/submissions/{sub_id}/label",
            }, 201)
            return

        # 4. API: Analis Lab Memverifikasi & Menerbitkan Sertifikat (Checker & Verifier)
        if path.startswith("/api/submissions/") and path.endswith("/verify"):
            sub_id = path.split("/")[3]
            if not _is_safe_id(sub_id):
                self._send_error_json("Format ID pengajuan tidak valid.", 400)
                return

            auth_user = self._get_authenticated_user()
            if auth_user:
                if auth_user["role"] not in ("analis_lab", "admin"):
                    self._send_error_json("Akses ditolak: Hanya Analis Laboratorium yang berwenang menerbitkan taksasi.", 403)
                    return
                analis_id = auth_user["user_id"]
            else:
                analis_id = int(body.get("analis_id", 2))

            conn = get_db_connection()
            cur = conn.cursor()
            # Ambil data pengajuan
            cur.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,))
            sub_row = cur.fetchone()
            if not sub_row:
                conn.close()
                self._send_error_json("ID Pengajuan tidak ditemukan", 404)
                return

            sub_data = dict(sub_row)
            if sub_data["status"] == "VERIFIED":
                conn.close()
                self._send_error_json(f"Sampel ini sudah diverifikasi sebelumnya dengan nomor sertifikat: {sub_data['nomor_sertifikat']}", 400)
                return

            # Ambil data analis lab dan verifikasi role
            cur.execute("SELECT id, nama_lengkap, nik_nip, instansi, role FROM users WHERE id = ?", (analis_id,))
            analis_row = cur.fetchone()
            if not analis_row or analis_row["role"] not in ("analis_lab", "admin"):
                conn.close()
                self._send_error_json("Akses ditolak: ID analis tidak valid atau tidak memiliki wewenang verifikasi lab.", 403)
                return

            analis_data = dict(analis_row)

            try:
                ka = float(body.get("kadar_air", 0.0))
                bp = float(body.get("butir_patah", 0.0))
                mn = float(body.get("butir_menir", 0.0))
                ba = float(body.get("benda_asing", 0.0))
            except (ValueError, TypeError):
                conn.close()
                self._send_error_json("Parameter pengujian laboratorium harus berupa angka numerik valid.", 400)
                return

            try:
                eval_res = evaluate_sample(ka, bp, mn, ba, sample_id=sub_id)
            except (ValueError, TypeError) as e:
                conn.close()
                self._send_error_json(str(e), 400)
                return

            cert_id = eval_res["nomor_sertifikat"]
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            kelas_mutu = eval_res["klasifikasi"]["kelas_mutu"]
            label_mutu = eval_res["klasifikasi"]["label_mutu"]
            harga_dasar = eval_res["rekomendasi_harga"]["harga_dasar"]
            penalti = eval_res["rekomendasi_harga"]["penalti_pengeringan"]
            penyusutan = eval_res["rekomendasi_harga"]["potongan_penyusutan"]
            harga_bersih = eval_res["rekomendasi_harga"]["harga_bersih"]

            # Buat Tanda Tangan Kriptografi HMAC-SHA256
            signature = generate_hmac_signature(
                sub_id,
                sub_data["petani_nik"],
                kelas_mutu,
                eval_res["tanggal_uji"],
                harga_bersih,
            )
            qr_url = f"/verify.html?id={cert_id}&sig={signature}"

            # Terbitkan Berkas PDF Resmi
            pdf_path = generate_certificate(
                eval_res,
                output_dir=OUTPUT_DIR,
                is_verified=True,
                petani_info={
                    "petani_nama": sub_data["petani_nama"],
                    "petani_nik": sub_data["petani_nik"],
                    "varietas_padi": sub_data["varietas_padi"],
                    "asal_lahan": sub_data["asal_lahan"],
                    "tonase_kg": sub_data["tonase_kg"],
                },
                analis_info={
                    "analis_nama": analis_data["nama_lengkap"],
                    "analis_nip": analis_data["nik_nip"],
                    "analis_instansi": analis_data["instansi"],
                },
                signature_hmac=signature,
                qr_url=qr_url,
            )

            # Simpan Sertifikat Resmi ke Database
            cur.execute(
                """
                INSERT INTO certificates (
                    nomor_sertifikat, submission_id, analis_id, analis_nama, analis_nip, analis_instansi,
                    petani_nama, petani_nik, varietas_padi, asal_lahan, tonase_kg, tanggal_uji,
                    kadar_air, butir_patah, butir_menir, benda_asing,
                    kelas_mutu, label_mutu, harga_dasar, penalti_pengeringan, potongan_penyusutan,
                    harga_bersih, signature_hmac, qr_url, pdf_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cert_id, sub_id, analis_id, analis_data["nama_lengkap"], analis_data["nik_nip"], analis_data["instansi"],
                    sub_data["petani_nama"], sub_data["petani_nik"], sub_data["varietas_padi"], sub_data["asal_lahan"], sub_data["tonase_kg"], eval_res["tanggal_uji"],
                    ka, bp, mn, ba,
                    kelas_mutu, label_mutu, harga_dasar, penalti, penyusutan,
                    harga_bersih, signature, qr_url, pdf_path, now_str,
                )
            )

            # Perbarui Status Pengajuan Petani
            cur.execute(
                """
                UPDATE submissions
                SET status = 'VERIFIED', verified_at = ?, verified_by = ?, nomor_sertifikat = ?
                WHERE id = ?
                """,
                (now_str, analis_id, cert_id, sub_id)
            )

            conn.commit()
            conn.close()

            log_audit(
                "VERIFY_AND_ISSUE_CERT",
                "CERTIFICATE",
                cert_id,
                {"sub_id": sub_id, "grade": kelas_mutu, "price": harga_bersih, "sig": signature},
                user_id=analis_id,
            )

            self._send_json({
                "success": True,
                "message": f"Sertifikat Mutu Resmi SNI {cert_id} berhasil diterbitkan dan ditandatangani digital!",
                "nomor_sertifikat": cert_id,
                "kelas_mutu": label_mutu,
                "harga_bersih": harga_bersih,
                "signature_hmac": signature,
                "qr_url": qr_url,
                "download_url": f"/api/certificates/{cert_id}/download",
            })
            return

        self._send_error_json("Endpoint POST tidak ditemukan", 404)


def run_server(port: int = PORT) -> None:
    """Menjalankan server web API multithreaded."""
    init_db()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(WEB_DIR, exist_ok=True)

    class ReusableTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with ReusableTCPServer(("", port), RiceQualityAPIHandler) as httpd:
        print("=" * 68)
        print(f" PELADEN RESMI SERTIFIKASI MUTU BERAS SNI 6128:2020 BERJALAN")
        print(f" Akses Web di : http://localhost:{port}/")
        print(f" Verifikasi di : http://localhost:{port}/verify.html")
        print(f" Dokumentasi   : Pustaka Standar Python 3.8+ (Zero Cloud Cost)")
        print("=" * 68)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nMematikan peladen...")
            httpd.shutdown()


if __name__ == "__main__":
    run_server(PORT)
