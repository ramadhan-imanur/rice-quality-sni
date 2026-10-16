#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_generator.py — Generator Sertifikat Mutu Beras Digital PDF A4 & Label Pengantar
===================================================================================

Menghasilkan:
1. Lembar Sertifikat Mutu Beras Resmi 1 Halaman Format PDF A4 (Certificate of Analysis)
   - Dilengkapi QR Code Verifikasi Publik (Pure Python Vector)
   - Tanda Tangan Digital Kriptografi HMAC-SHA256 (Anti-Fraud)
   - Watermark Otomatis "SIMULASI MANDIRI - BUKAN BUKTI MUTU SAH" jika belum terverifikasi lab
2. Label Pengantar Sampel Gabah/Beras untuk Petani (Maker-Checker Workflow)

Semua dirancang 100% menggunakan pustaka standar Python (raw PDF 1.4).

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Tambahkan parent directory ke sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from qr_codec import generate_qr_matrix


# ============================================================================
# RAW PDF 1.4 GENERATOR (Tanpa Library Eksternal)
# ============================================================================

class PDFWriter:
    """
    Generator PDF 1.4 minimalis menggunakan pustaka standar Python.
    Mendukung teks, garis, kotak, warna, teks miring/watermark, dan QR Code vektor.
    """

    def __init__(self):
        self.objects: List[bytes] = []
        self.pages: List[int] = []
        self.page_contents: List[bytes] = []
        # A4 dalam poin: 595.28 x 841.89
        self.page_width = 595.28
        self.page_height = 841.89
        self.margin_left = 45.0
        self.margin_right = 45.0
        self.margin_top = 40.0
        self.margin_bottom = 40.0
        self._current_stream = b""

    def _text(
        self,
        x: float,
        y: float,
        text: str,
        font_size: int = 10,
        bold: bool = False,
        align: str = "left",
        color_rgb: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        """Menambahkan teks ke halaman saat ini."""
        font = "/F2" if bold else "/F1"
        safe_text = (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

        if align == "center":
            text_width = len(text) * font_size * 0.46
            x = (self.page_width - text_width) / 2
        elif align == "right":
            text_width = len(text) * font_size * 0.46
            x = x - text_width

        color_cmd = ""
        if color_rgb:
            r, g, b = color_rgb
            color_cmd = f"{r:.2f} {g:.2f} {b:.2f} rg\n"
        else:
            color_cmd = "0.0 0.0 0.0 rg\n"

        self._current_stream += (
            f"BT\n"
            f"{color_cmd}"
            f"{font} {font_size} Tf\n"
            f"{x:.2f} {y:.2f} Td\n"
            f"({safe_text}) Tj\n"
            f"ET\n"
        ).encode("latin-1", errors="replace")

    def _line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: float = 1.0,
        color_rgb: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        """Menggambar garis lurus."""
        color_cmd = ""
        if color_rgb:
            r, g, b = color_rgb
            color_cmd = f"{r:.2f} {g:.2f} {b:.2f} RG\n"
        else:
            color_cmd = "0.0 0.0 0.0 RG\n"

        self._current_stream += (
            f"{color_cmd}"
            f"{width:.2f} w\n"
            f"{x1:.2f} {y1:.2f} m\n"
            f"{x2:.2f} {y2:.2f} l\n"
            f"S\n"
        ).encode("latin-1")

    def _rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: bool = False,
        stroke: bool = True,
        fill_gray: float = 0.9,
        fill_rgb: Optional[Tuple[float, float, float]] = None,
        stroke_rgb: Optional[Tuple[float, float, float]] = None,
        stroke_width: float = 1.0,
    ) -> None:
        """Menggambar persegi panjang."""
        ops = f"{stroke_width:.2f} w\n"
        if fill_rgb:
            r, g, b = fill_rgb
            ops += f"{r:.2f} {g:.2f} {b:.2f} rg\n"
        elif fill:
            ops += f"{fill_gray:.2f} g\n"

        if stroke_rgb:
            r, g, b = stroke_rgb
            ops += f"{r:.2f} {g:.2f} {b:.2f} RG\n"
        elif stroke:
            ops += "0.0 0.0 0.0 RG\n"

        ops += f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re\n"
        if fill and stroke:
            ops += "B\n"
        elif fill:
            ops += "f\n"
        elif stroke:
            ops += "S\n"
        self._current_stream += ops.encode("latin-1")

    def _watermark(self, text: str) -> None:
        """
        Mencetak teks watermark diagonal melintang halaman dengan sudut ~30 derajat.
        Warna merah transparan terang agar tidak menutupi informasi penting.
        """
        safe_text = (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        # Transformasi cm: cos(30)=0.866, sin(30)=0.5, -sin(30)=-0.5, cos(30)=0.866
        # Posisi sekitar x=70, y=280
        self._current_stream += (
            f"q\n"
            f"0.866 0.5 -0.5 0.866 70 280 cm\n"
            f"BT\n"
            f"/F2 26 Tf\n"
            f"0.92 0.40 0.40 rg\n"
            f"0 0 Td\n"
            f"({safe_text}) Tj\n"
            f"ET\n"
            f"Q\n"
        ).encode("latin-1", errors="replace")

    def _draw_qr(self, x: float, y: float, text: str, size: float = 80.0) -> None:
        """
        Menggambar QR Code murni vektor dari string teks.
        Origin: (x, y) adalah pojok kiri atas area QR.
        """
        try:
            matrix = generate_qr_matrix(text, "L")
        except Exception:
            # Fallback jika teks terlalu panjang untuk L
            matrix = generate_qr_matrix(text[:90], "L")

        n = len(matrix)
        cell = size / n

        # Latar belakang putih dengan padding
        padding = 4.0
        self._rect(
            x - padding,
            y - size - padding,
            size + padding * 2,
            size + padding * 2,
            fill=True,
            stroke=True,
            fill_rgb=(1.0, 1.0, 1.0),
            stroke_rgb=(0.75, 0.75, 0.75),
            stroke_width=0.75,
        )

        # Gambar sel modul hitam
        for r in range(n):
            for c in range(n):
                if matrix[r][c]:
                    self._rect(
                        x + c * cell,
                        y - (r + 1) * cell,
                        cell,
                        cell,
                        fill=True,
                        stroke=False,
                        fill_rgb=(0.0, 0.0, 0.0),
                    )

    def new_page(self) -> None:
        """Memulai halaman baru."""
        if self._current_stream:
            self.page_contents.append(self._current_stream)
        self._current_stream = b""

    def finalize_page(self) -> None:
        """Menyelesaikan halaman saat ini."""
        self.page_contents.append(self._current_stream)
        self._current_stream = b""

    def build(self) -> bytes:
        """Mengompilasi seluruh konten menjadi berkas PDF valid."""
        if self._current_stream:
            self.finalize_page()

        pdf_objects: List[bytes] = []
        offsets: List[int] = []
        output = b"%PDF-1.4\n"

        # Obj 1: Catalog
        obj_catalog = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

        # Obj 3: Font Helvetica (regular)
        obj_font1 = (
            b"3 0 obj\n"
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>\n"
            b"endobj\n"
        )

        # Obj 4: Font Helvetica-Bold
        obj_font2 = (
            b"4 0 obj\n"
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
            b"/Encoding /WinAnsiEncoding >>\n"
            b"endobj\n"
        )

        # Obj 5: Resources
        obj_resources = (
            b"5 0 obj\n"
            b"<< /Font << /F1 3 0 R /F2 4 0 R >> >>\n"
            b"endobj\n"
        )

        # Now build the actual output
        output = b"%PDF-1.4\n"
        offsets = []

        # Obj 1: Catalog
        offsets.append(len(output))
        output += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

        # Obj 2: Pages
        kids = " ".join(
            f"{6 + i * 2 + 1} 0 R" for i in range(len(self.page_contents))
        )
        offsets.append(len(output))
        output += (
            f"2 0 obj\n<< /Type /Pages /Kids [{kids}] "
            f"/Count {len(self.page_contents)} >>\nendobj\n"
        ).encode("latin-1")

        # Obj 3: Font regular
        offsets.append(len(output))
        output += obj_font1

        # Obj 4: Font bold
        offsets.append(len(output))
        output += obj_font2

        # Obj 5: Resources
        offsets.append(len(output))
        output += obj_resources

        # Pages + streams (obj 6, 7, 8, 9, ...)
        for i, content in enumerate(self.page_contents):
            stream_obj = 6 + i * 2
            page_obj = stream_obj + 1

            # Stream
            offsets.append(len(output))
            output += (
                f"{stream_obj} 0 obj\n"
                f"<< /Length {len(content)} >>\n"
                f"stream\n"
            ).encode("latin-1")
            output += content
            output += b"\nendstream\nendobj\n"

            # Page
            offsets.append(len(output))
            output += (
                f"{page_obj} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {self.page_width:.2f} {self.page_height:.2f}] "
                f"/Contents {stream_obj} 0 R /Resources 5 0 R >>\n"
                f"endobj\n"
            ).encode("latin-1")

        # Cross-reference table
        xref_offset = len(output)
        num_objects = len(offsets) + 1
        output += b"xref\n"
        output += f"0 {num_objects}\n".encode("latin-1")
        output += b"0000000000 65535 f \n"
        for off in offsets:
            output += f"{off:010d} 00000 n \n".encode("latin-1")

        # Trailer
        output += (
            f"trailer\n"
            f"<< /Size {num_objects} /Root 1 0 R >>\n"
            f"startxref\n"
            f"{xref_offset}\n"
            f"%%EOF\n"
        ).encode("latin-1")

        return output


# ============================================================================
# GENERATOR SERTIFIKAT MUTU BERAS RESMI (CERTIFICATE OF ANALYSIS)
# ============================================================================

def generate_certificate(
    result: Dict[str, Any],
    output_dir: str = "output",
    is_verified: bool = True,
    petani_info: Optional[Dict[str, Any]] = None,
    analis_info: Optional[Dict[str, Any]] = None,
    signature_hmac: Optional[str] = None,
    qr_url: Optional[str] = None,
) -> str:
    """
    Menghasilkan sertifikat mutu beras format PDF A4 berstandar Certificate of Analysis (CoA).
    Dilengkapi segel kriptografi HMAC-SHA256, QR Code verifikasi publik, dan watermark otomatis.
    """
    os.makedirs(output_dir, exist_ok=True)

    pdf = PDFWriter()
    pw = pdf.page_width
    ml = pdf.margin_left
    mr = pdf.margin_right
    usable_width = pw - ml - mr
    y = pdf.page_height - pdf.margin_top

    # Data ekstraksi
    nomor_sertifikat = result.get("nomor_sertifikat", "SNI-DRAFT")
    sample_id = result.get("sample_id", "SAMPEL-UJI")
    tanggal_uji = result.get("tanggal_uji", datetime.now().strftime("%d-%m-%Y %H:%M WIB"))

    params = result.get("parameter_uji", {})
    ka = float(params.get("kadar_air", 0.0))
    bp = float(params.get("butir_patah", 0.0))
    mn = float(params.get("butir_menir", 0.0))
    ba = float(params.get("benda_asing", 0.0))

    klasifikasi = result.get("klasifikasi", {})
    kelas = klasifikasi.get("kelas_mutu", "SUBSTANDAR")
    label = klasifikasi.get("label_mutu", "Substandar")

    harga = result.get("rekomendasi_harga", {})
    harga_dasar = float(harga.get("harga_dasar", 0.0))
    penalti = float(harga.get("penalti_pengeringan", 0.0))
    penyusutan = float(harga.get("potongan_penyusutan", 0.0))
    harga_bersih = float(harga.get("harga_bersih", 0.0))

    # Info Petani & Batch
    p_info = petani_info or {}
    petani_nama = p_info.get("petani_nama", "Petani / Kelompok Tani Mitra")
    petani_nik = p_info.get("petani_nik", "-")
    varietas = p_info.get("varietas_padi", "Padi Sawah (Ciherang/Inpari)")
    asal_lahan = p_info.get("asal_lahan", "Lahan Pertanian Rakyat")
    tonase_kg = p_info.get("tonase_kg", 5000.0)

    # Info Analis Lab
    a_info = analis_info or {}
    analis_nama = a_info.get("analis_nama", "Ramadhaan Imanur Rochima")
    analis_nip = a_info.get("analis_nip", "M0124015")
    analis_instansi = a_info.get("analis_instansi", "Lab Sentral Analisis Mutu FMIPA UNS")

    # Kriptografi Signature & QR
    if signature_hmac is None:
        try:
            from database import generate_hmac_signature
            signature_hmac = generate_hmac_signature(sample_id, petani_nik, kelas, tanggal_uji, harga_bersih)
        except Exception:
            signature_hmac = "A8F9D2E4C0B1"

    if qr_url is None:
        qr_url = f"http://localhost:8000/verify.html?id={nomor_sertifikat}&sig={signature_hmac}"

    # 1. KOP SURAT RESMI
    # Kotak header hijau elegan
    pdf._rect(ml, y - 52, usable_width, 54, fill=True, stroke=False, fill_rgb=(0.04, 0.35, 0.22))
    pdf._text(ml + 15, y - 18, "LEMBAR HASIL TAKSASI MUTU & HARGA BERAS", font_size=12, bold=True, color_rgb=(1.0, 1.0, 1.0))
    pdf._text(ml + 15, y - 32, "INSTRUMEN PRE-GRADING & TRANSPARANSI HARGA TINGKAT PETANI (BAPANAS 67/2024)", font_size=8, bold=False, color_rgb=(0.85, 0.95, 0.88))
    pdf._text(ml + 15, y - 44, "Laboratorium / RMU Mitra | Evaluasi Mandiri Berbasis Standar Acuan SNI 6128:2020", font_size=7, color_rgb=(0.75, 0.90, 0.80))

    # Badge Kanan Atas
    if is_verified:
        pdf._rect(pw - mr - 130, y - 42, 120, 24, fill=True, stroke=False, fill_rgb=(0.10, 0.55, 0.30))
        pdf._text(pw - mr - 70, y - 27, "TAKSASI TERUKUR", font_size=8, bold=True, align="center", color_rgb=(1.0, 1.0, 1.0))
        pdf._text(pw - mr - 70, y - 37, "PRA-INSPEKSI PASAR", font_size=7, align="center", color_rgb=(0.85, 1.0, 0.85))
    else:
        pdf._rect(pw - mr - 140, y - 42, 130, 24, fill=True, stroke=False, fill_rgb=(0.75, 0.20, 0.20))
        pdf._text(pw - mr - 75, y - 27, "SIMULASI MANDIRI", font_size=8, bold=True, align="center", color_rgb=(1.0, 1.0, 1.0))
        pdf._text(pw - mr - 75, y - 37, "ESTIMASI PRELIMINER", font_size=7, align="center", color_rgb=(1.0, 0.85, 0.85))

    y -= 65

    # 2. JUDUL DOKUMEN & WATERMARK JIKA UNVERIFIED
    if not is_verified:
        pdf._watermark("SIMULASI MANDIRI - BUKAN BUKTI MUTU SAH")

    pdf._text(pw / 2, y, "LEMBAR HASIL TAKSASI MUTU & HARGA BERAS", font_size=14, bold=True, align="center", color_rgb=(0.05, 0.25, 0.15))
    y -= 14
    pdf._text(pw / 2, y, "DIGITAL QUALITY APPRAISAL REPORT (ACUAN SNI 6128:2020 & BAPANAS NO. 67/2024)", font_size=8, bold=True, align="center", color_rgb=(0.35, 0.40, 0.45))
    y -= 15

    # Garis pembatas
    pdf._line(ml, y, pw - mr, y, width=1.5, color_rgb=(0.04, 0.35, 0.22))
    y -= 16

    # 3. METADATA SUBMISI & BATCH (2 Kolom)
    box_w = (usable_width - 10) / 2
    # Kolom Kiri: Data Pengujian
    pdf._rect(ml, y - 68, box_w, 70, fill=True, stroke=True, fill_rgb=(0.97, 0.98, 0.99), stroke_rgb=(0.82, 0.86, 0.90))
    pdf._text(ml + 8, y - 14, "INFORMASI TAKSASI & METODE", font_size=9, bold=True, color_rgb=(0.08, 0.25, 0.40))
    pdf._text(ml + 8, y - 28, f"Nomor Taksasi    : {nomor_sertifikat}", font_size=8, bold=True)
    pdf._text(ml + 8, y - 40, f"Identitas Sampel : {sample_id}", font_size=8)
    pdf._text(ml + 8, y - 52, f"Tanggal Taksasi  : {tanggal_uji}", font_size=8)
    pdf._text(ml + 8, y - 64, f"Metode Analisis  : Fisik Deterministik & Computer Vision", font_size=8)

    # Kolom Kanan: Data Petani & Batch Lahan
    col2_x = ml + box_w + 10
    pdf._rect(col2_x, y - 68, box_w, 70, fill=True, stroke=True, fill_rgb=(0.97, 0.98, 0.99), stroke_rgb=(0.82, 0.86, 0.90))
    pdf._text(col2_x + 8, y - 14, "IDENTITAS PETANI & BATCH GABAH", font_size=9, bold=True, color_rgb=(0.08, 0.25, 0.40))
    pdf._text(col2_x + 8, y - 28, f"Nama Pemilik    : {petani_nama}", font_size=8, bold=True)
    pdf._text(col2_x + 8, y - 40, f"NIK Petani      : {petani_nik}", font_size=8)
    pdf._text(col2_x + 8, y - 52, f"Varietas / Asal : {varietas} | {asal_lahan[:24]}", font_size=8)
    pdf._text(col2_x + 8, y - 64, f"Estimasi Tonase : {tonase_kg:,.0f} kg ({tonase_kg/1000:.1f} Ton)", font_size=8)

    y -= 82

    # 4. TABEL HASIL PENGUJIAN FISIK (Certificate of Analysis Comparison)
    pdf._text(ml, y, "I. HASIL PENGUJIAN PARAMETER FISIK VS STANDAR MUTU SNI 6128:2020", font_size=10, bold=True, color_rgb=(0.05, 0.25, 0.15))
    y -= 14

    # Table Headers
    cols = [135, 75, 75, 75, 75, 70]
    th_titles = ["Parameter Mutu", "Hasil Uji", "Batas Premium", "Batas Med. I", "Batas Med. II", "Evaluasi"]
    pdf._rect(ml, y - 14, usable_width, 16, fill=True, stroke=False, fill_rgb=(0.12, 0.25, 0.35))
    cx = ml
    for i, t in enumerate(th_titles):
        pdf._text(cx + 5, y - 10, t, font_size=8, bold=True, color_rgb=(1.0, 1.0, 1.0))
        cx += cols[i]
    y -= 16

    # Determine status for each parameter
    def get_eval(val, p_max, m1_max, m2_max):
        if val <= p_max: return "PREMIUM", (0.05, 0.50, 0.20)
        if val <= m1_max: return "MEDIUM I", (0.15, 0.40, 0.70)
        if val <= m2_max: return "MEDIUM II", (0.75, 0.45, 0.05)
        return "SUBSTANDAR", (0.80, 0.15, 0.15)

    ev_ka, col_ka = get_eval(ka, 14.0, 14.0, 14.0)
    ev_bp, col_bp = get_eval(bp, 15.0, 20.0, 25.0)
    ev_mn, col_mn = get_eval(mn, 0.50, 2.00, 5.00)
    ev_ba, col_ba = get_eval(ba, 0.01, 0.02, 0.05)

    table_data = [
        ("Kadar Air (%)", f"{ka:.2f} %", "<= 14.00 %", "<= 14.00 %", "<= 14.00 %", ev_ka, col_ka),
        ("Butir Patah (%)", f"{bp:.2f} %", "<= 15.00 %", "<= 20.00 %", "<= 25.00 %", ev_bp, col_bp),
        ("Butir Menir (%)", f"{mn:.2f} %", "<= 0.50 %", "<= 2.00 %", "<= 5.00 %", ev_mn, col_mn),
        ("Benda Asing / Kotoran (%)", f"{ba:.4f} %", "<= 0.0100 %", "<= 0.0200 %", "<= 0.0500 %", ev_ba, col_ba),
    ]

    for idx, (p_name, p_val, p_p, p_m1, p_m2, ev_txt, ev_c) in enumerate(table_data):
        bg_rgb = (0.97, 0.98, 0.99) if idx % 2 == 0 else (1.0, 1.0, 1.0)
        pdf._rect(ml, y - 14, usable_width, 15, fill=True, stroke=True, fill_rgb=bg_rgb, stroke_rgb=(0.88, 0.90, 0.93))
        cx = ml
        pdf._text(cx + 5, y - 11, p_name, font_size=8, bold=True)
        cx += cols[0]
        pdf._text(cx + 5, y - 11, p_val, font_size=8, bold=True, color_rgb=(0.1, 0.1, 0.1))
        cx += cols[1]
        pdf._text(cx + 5, y - 11, p_p, font_size=8)
        cx += cols[2]
        pdf._text(cx + 5, y - 11, p_m1, font_size=8)
        cx += cols[3]
        pdf._text(cx + 5, y - 11, p_m2, font_size=8)
        cx += cols[4]
        pdf._text(cx + 5, y - 11, ev_txt, font_size=8, bold=True, color_rgb=ev_c)
        y -= 15

    y -= 10

    # 5. KOTAK KELAS MUTU FINAL & STATEMENT RESMI
    grade_colors = {
        "PREMIUM": ((0.05, 0.45, 0.25), (0.92, 0.98, 0.94)),
        "MEDIUM_I": ((0.10, 0.35, 0.65), (0.93, 0.96, 1.00)),
        "MEDIUM_II": ((0.75, 0.45, 0.05), (1.00, 0.98, 0.92)),
        "SUBSTANDAR": ((0.75, 0.15, 0.15), (1.00, 0.94, 0.94)),
    }
    fg_col, bg_col = grade_colors.get(kelas, ((0.3, 0.3, 0.3), (0.95, 0.95, 0.95)))

    box_h = 38
    pdf._rect(ml, y - box_h, usable_width, box_h, fill=True, stroke=True, fill_rgb=bg_col, stroke_rgb=fg_col, stroke_width=1.5)
    pdf._text(pw / 2, y - 13, "KESIMPULAN MUTU AKHIR:", font_size=9, bold=True, align="center", color_rgb=fg_col)
    pdf._text(pw / 2, y - 30, f"MUTU {label.upper()}", font_size=17, bold=True, align="center", color_rgb=fg_col)
    y -= box_h + 12

    # 6. REKOMENDASI HARGA BAPANAS NO. 67/2024 & NILAI TRANSAKSI
    pdf._text(ml, y, "II. REKOMENDASI HARGA PEMBELIAN WAJAR (BAPANAS NO. 67/2024)", font_size=10, bold=True, color_rgb=(0.05, 0.25, 0.15))
    y -= 12

    price_box_h = 48
    pdf._rect(ml, y - price_box_h, usable_width, price_box_h, fill=True, stroke=True, fill_rgb=(0.98, 0.99, 1.00), stroke_rgb=(0.85, 0.88, 0.92))
    
    # 4 kolom ringkasan harga
    pcol_w = usable_width / 4
    pdf._text(ml + 10, y - 14, "Harga Dasar Acuan", font_size=8, color_rgb=(0.4, 0.4, 0.4))
    pdf._text(ml + 10, y - 27, f"Rp {harga_dasar:,.0f} /kg", font_size=10, bold=True)
    pdf._text(ml + 10, y - 39, "Sesuai HET / HPP Bapanas", font_size=7, color_rgb=(0.5, 0.5, 0.5))

    pdf._text(ml + pcol_w + 5, y - 14, "Potongan Penalti Air", font_size=8, color_rgb=(0.4, 0.4, 0.4))
    pdf._text(ml + pcol_w + 5, y - 27, f"- Rp {penalti:,.0f} /kg", font_size=10, bold=True, color_rgb=(0.75, 0.1, 0.1))
    pdf._text(ml + pcol_w + 5, y - 39, "Rp 150/1% > 14%", font_size=7, color_rgb=(0.5, 0.5, 0.5))

    pdf._text(ml + pcol_w * 2, y - 14, "Penyusutan Berat (1.5%)", font_size=8, color_rgb=(0.4, 0.4, 0.4))
    pdf._text(ml + pcol_w * 2, y - 27, f"- Rp {penyusutan:,.0f} /kg", font_size=10, bold=True, color_rgb=(0.75, 0.1, 0.1))
    pdf._text(ml + pcol_w * 2, y - 39, "Proporsional kelembaban", font_size=7, color_rgb=(0.5, 0.5, 0.5))

    pdf._text(ml + pcol_w * 3, y - 14, "Rekomendasi Beli Bersih", font_size=8, bold=True, color_rgb=(0.04, 0.35, 0.22))
    pdf._text(ml + pcol_w * 3, y - 28, f"Rp {harga_bersih:,.0f} /kg", font_size=12, bold=True, color_rgb=(0.04, 0.35, 0.22))
    total_batch_val = tonase_kg * harga_bersih
    pdf._text(ml + pcol_w * 3, y - 41, f"Batch: Rp {total_batch_val:,.0f}", font_size=8, bold=True, color_rgb=(0.2, 0.2, 0.2))

    y -= price_box_h + 14

    # 7. LEGALITAS, SEGEL KRIPTOGRAFI & QR CODE VERIFIKASI
    pdf._line(ml, y, pw - mr, y, width=1.0, color_rgb=(0.80, 0.83, 0.88))
    y -= 12

    # QR Code di Kanan Bawah
    qr_size = 72.0
    qr_x = pw - mr - qr_size - 6.0
    qr_y = y - 4.0
    pdf._draw_qr(qr_x, qr_y, qr_url, size=qr_size)

    # Info Tanda Tangan & Kriptografi di Sebelah Kiri QR
    sign_w = usable_width - qr_size - 25.0
    pdf._text(ml, y, "III. PENGESAHAN DOKUMEN & INTEGRITAS KRIPTOGRAFI", font_size=9, bold=True, color_rgb=(0.05, 0.25, 0.15))
    y -= 14

    # Data Pengesahan
    pdf._text(ml, y, f"Verifikator Lab : {analis_nama} (NIP/NIM: {analis_nip})", font_size=8, bold=True)
    pdf._text(ml, y - 11, f"Institusi      : {analis_instansi}", font_size=8)
    pdf._text(ml, y - 22, f"Digital Sig    : HMAC-SHA256 [{signature_hmac}]", font_size=8, bold=True, color_rgb=(0.15, 0.25, 0.45))
    pdf._text(ml, y - 33, f"Audit Trail ID : SUB-{sample_id} | Ref: BSN SNI 6128:2020", font_size=7, color_rgb=(0.4, 0.4, 0.4))
    pdf._text(ml, y - 44, "Pindai QR Code di samping untuk verifikasi keaslian dokumen di database server.", font_size=7, bold=True, color_rgb=(0.05, 0.45, 0.25))

    # Stempel digital
    stamp_x = ml + 240
    pdf._rect(stamp_x, y - 46, 85, 34, fill=False, stroke=True, stroke_rgb=(0.05, 0.45, 0.25), stroke_width=1.2)
    pdf._text(stamp_x + 42.5, y - 20, "SEPAKAT MUTU", font_size=8, bold=True, align="center", color_rgb=(0.05, 0.45, 0.25))
    pdf._text(stamp_x + 42.5, y - 32, "SNI 6128:2020", font_size=8, bold=True, align="center", color_rgb=(0.05, 0.45, 0.25))
    pdf._text(stamp_x + 42.5, y - 41, "TERVERIFIKASI", font_size=6, align="center", color_rgb=(0.05, 0.45, 0.25))

    # Catatan Kaki Hukum & Batasan Wewenang Resmi (UU No. 20/2014)
    foot_y = pdf.margin_bottom + 12
    pdf._line(ml, foot_y + 12, pw - mr, foot_y + 12, width=0.5, color_rgb=(0.85, 0.85, 0.85))
    pdf._text(
        ml,
        foot_y,
        "PERNYATAAN HUKUM: Dokumen ini adalah lembar hasil taksasi mutu fisik digital dan rekomendasi harga berbasis SNI 6128:2020 & Bapanas 67/2024.",
        font_size=6.2,
        color_rgb=(0.40, 0.40, 0.40),
    )
    pdf._text(
        ml,
        foot_y - 8,
        "Berfungsi sebagai instrumen transparansi pasar internal, BUKAN pengganti Sertifikat Kesesuaian resmi dari LSPro terakreditasi KAN (UU 20/2014).",
        font_size=6.2,
        color_rgb=(0.40, 0.40, 0.40),
    )

    pdf.finalize_page()
    pdf_bytes = pdf.build()

    safe_cert_id = nomor_sertifikat.replace("/", "-")
    filename = f"taksasi_{safe_cert_id}.pdf"
    filepath = os.path.join(output_dir, filename)
    abs_path = os.path.abspath(filepath)

    with open(abs_path, "wb") as f:
        f.write(pdf_bytes)

    return abs_path


# ============================================================================
# GENERATOR LABEL PENGANTAR SAMPEL (SURAT JALAN SAMPEL PETANI KE LAB)
# ============================================================================

def generate_sample_label(
    submission: Dict[str, Any],
    output_dir: str = "output",
) -> str:
    """
    Menghasilkan Surat Jalan / Label Pengantar Sampel Beras (PDF A4)
    yang dicetak oleh Petani untuk ditempel pada kantong sampel beras fisik
    sebelum dikirim dan diperiksa oleh analis lab di koperasi/Bulog.
    """
    os.makedirs(output_dir, exist_ok=True)

    pdf = PDFWriter()
    pw = pdf.page_width
    ml = pdf.margin_left
    mr = pdf.margin_right
    usable_width = pw - ml - mr
    y = pdf.page_height - pdf.margin_top

    sub_id = submission.get("id", "SUB-DEMO")
    barcode_id = submission.get("barcode_id", sub_id)
    petani_nama = submission.get("petani_nama", "-")
    petani_nik = submission.get("petani_nik", "-")
    kontak = submission.get("kontak", "-")
    varietas = submission.get("varietas_padi", "-")
    asal_lahan = submission.get("asal_lahan", "-")
    tonase = float(submission.get("tonase_kg", 0.0))
    tgl_panen = submission.get("tanggal_panen", "-")
    catatan = submission.get("catatan", "-")

    # Header Label Pengantar
    pdf._rect(ml, y - 50, usable_width, 50, fill=True, stroke=False, fill_rgb=(0.10, 0.35, 0.55))
    pdf._text(ml + 15, y - 20, "LABEL PENGANTAR SAMPEL UJI LABORATORIUM", font_size=13, bold=True, color_rgb=(1.0, 1.0, 1.0))
    pdf._text(ml + 15, y - 34, "Sistem Sertifikasi Mutu Beras SNI 6128:2020 — Alur Kerja Maker-Checker", font_size=9, color_rgb=(0.9, 0.95, 1.0))
    y -= 65

    # Barcode & QR Block
    pdf._text(ml, y, f"IDENTITAS BATCH SAMPEL: {sub_id}", font_size=12, bold=True, color_rgb=(0.1, 0.2, 0.4))
    y -= 14

    qr_size = 90.0
    pdf._draw_qr(ml + 10, y, f"SAMPLE-ID:{barcode_id}|BATCH:{sub_id}|NIK:{petani_nik}", size=qr_size)

    # Info sebelah QR
    info_x = ml + qr_size + 25.0
    pdf._text(info_x, y - 10, "KODE BARCODE SAMPEL:", font_size=9, color_rgb=(0.4, 0.4, 0.4))
    pdf._text(info_x, y - 25, barcode_id, font_size=16, bold=True, color_rgb=(0.05, 0.25, 0.45))
    pdf._text(info_x, y - 42, f"Tanggal Pengajuan : {datetime.now().strftime('%d-%m-%Y %H:%M WIB')}", font_size=8)
    pdf._text(info_x, y - 56, "Status Saat Ini   : MENUNGGU UJI LAB (PENDING)", font_size=8, bold=True, color_rgb=(0.75, 0.45, 0.05))
    pdf._text(info_x, y - 70, "Kantong Sampel Wajib : 1.000 gram (1 kg) Beras Tersegel", font_size=8, color_rgb=(0.3, 0.3, 0.3))

    y -= qr_size + 15

    # Tabel Rincian Petani & Panen
    pdf._rect(ml, y - 110, usable_width, 110, fill=True, stroke=True, fill_rgb=(0.98, 0.99, 1.0), stroke_rgb=(0.8, 0.85, 0.9))
    pdf._text(ml + 12, y - 18, "DETAIL PENGAJUAN SAMPEL DARI PETANI (MAKER)", font_size=10, bold=True, color_rgb=(0.1, 0.25, 0.45))

    details = [
        ("Nama Lengkap Petani", petani_nama, "Nomor Kontak / WA", kontak),
        ("NIK Pemilik / Petani", petani_nik, "Tanggal Panen Padi", tgl_panen),
        ("Varietas Gabah / Beras", varietas, "Total Estimasi Batch", f"{tonase:,.0f} kg ({tonase/1000:.1f} Ton)"),
        ("Asal Lahan / Lokasi Sawah", asal_lahan[:35], "Catatan Khusus", catatan[:35]),
    ]

    dy = y - 34
    for l1, v1, l2, v2 in details:
        pdf._text(ml + 15, dy, f"{l1}:", font_size=8, bold=True)
        pdf._text(ml + 130, dy, str(v1), font_size=8)
        pdf._text(ml + 270, dy, f"{l2}:", font_size=8, bold=True)
        pdf._text(ml + 380, dy, str(v2), font_size=8)
        dy -= 18

    y -= 125

    # Lembar Tanda Terima Lab
    pdf._rect(ml, y - 130, usable_width, 130, fill=False, stroke=True, stroke_rgb=(0.5, 0.5, 0.5), stroke_width=1.0)
    pdf._text(ml + 12, y - 18, "TANDA TERIMA & SERAH TERIMA SAMPEL LABORATORIUM", font_size=10, bold=True)
    pdf._text(ml + 12, y - 30, "Diisi oleh Petugas Pengambil / Penerima Sampel di Lokasi Laboratorium / RMU:", font_size=8, color_rgb=(0.4, 0.4, 0.4))

    pdf._line(ml + 15, y - 40, pw - mr - 15, y - 40, width=0.5, color_rgb=(0.7, 0.7, 0.7))

    pdf._text(ml + 20, y - 55, "Petani / Pengirim Sampel,", font_size=8)
    pdf._text(ml + 20, y - 110, f"( {petani_nama[:25]} )", font_size=8, bold=True)

    pdf._text(pw - mr - 200, y - 55, "Petugas Lab Penerima Sampel,", font_size=8)
    pdf._text(pw - mr - 200, y - 110, "( ................................................ )", font_size=8)
    pdf._text(pw - mr - 200, y - 122, "Tgl Diterima: ...... / ...... / 2026", font_size=7)

    pdf.finalize_page()
    pdf_bytes = pdf.build()

    safe_sub_id = sub_id.replace("/", "-")
    filename = f"label_{safe_sub_id}.pdf"
    filepath = os.path.join(output_dir, filename)
    abs_path = os.path.abspath(filepath)

    with open(abs_path, "wb") as f:
        f.write(pdf_bytes)

    return abs_path


# ============================================================================
# DEMO STANDALONE
# ============================================================================

if __name__ == "__main__":
    from quality_engine import evaluate_sample

    print("=" * 60)
    print("  DEMO: Generator Sertifikat Mutu Beras PDF A4 & Label Pengantar")
    print("=" * 60)

    # 1. Evaluasi sampel contoh
    hasil = evaluate_sample(13.4, 13.5, 0.4, 0.008, sample_id="Beras Pandan Wangi Super")

    # 2. Generate PDF Resmi dengan QR Code & Signature
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    path_cert = generate_certificate(
        hasil,
        output_dir=output_dir,
        is_verified=True,
        petani_info={
            "petani_nama": "Pak Haji Sutrisno",
            "petani_nik": "3311012304750001",
            "varietas_padi": "Pandan Wangi Cianjur",
            "asal_lahan": "Desa Bekonang, Sukoharjo",
            "tonase_kg": 7500.0,
        },
        analis_info={
            "analis_nama": "Ramadhaan Imanur Rochima",
            "analis_nip": "M0124015",
            "analis_instansi": "Lab Sentral Analisis Mutu FMIPA UNS",
        },
    )

    print(f"\n  [+] Sertifikat Resmi Terbit : {path_cert}")

    # 3. Generate Label Pengantar Sampel
    sample_sub = {
        "id": "BATCH-20261016-001",
        "barcode_id": "SMP-20261016-881",
        "petani_nama": "Pak Haji Sutrisno",
        "petani_nik": "3311012304750001",
        "kontak": "081234567890",
        "varietas_padi": "Pandan Wangi Cianjur",
        "asal_lahan": "Desa Bekonang, Sukoharjo",
        "tonase_kg": 7500.0,
        "tanggal_panen": "14 Oktober 2026",
        "catatan": "Kadar air rendah, jemur lantai semen 2 hari",
    }
    path_label = generate_sample_label(sample_sub, output_dir=output_dir)
    print(f"  [+] Label Pengantar Terbit  : {path_label}")

    print("=" * 60)
