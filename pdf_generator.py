#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_generator.py — Generator Sertifikat Mutu Beras Digital PDF A4
=================================================================

Menghasilkan lembar sertifikat mutu beras resmi 1 halaman format PDF A4
secara lokal tanpa dependensi pustaka pihak ketiga (raw PDF 1.4).

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# Tambahkan parent directory ke sys.path
sys.path.insert(0, os.path.dirname(__file__))


# ============================================================================
# RAW PDF 1.4 GENERATOR (Tanpa Library Eksternal)
# ============================================================================

class PDFWriter:
    """
    Generator PDF 1.4 minimalis menggunakan pustaka standar Python.
    Mendukung teks, garis, kotak, dan tabel sederhana di atas kertas A4.
    """

    def __init__(self):
        self.objects: List[bytes] = []
        self.pages: List[int] = []
        self.page_contents: List[bytes] = []
        # A4 dalam poin: 595.28 x 841.89
        self.page_width = 595.28
        self.page_height = 841.89
        self.margin_left = 50
        self.margin_right = 50
        self.margin_top = 50
        self.margin_bottom = 50
        self._current_stream = b""

    def _add_object(self, content: bytes) -> int:
        """Menambahkan objek PDF dan mengembalikan nomor objek (1-indexed)."""
        self.objects.append(content)
        return len(self.objects)

    def _text(self, x: float, y: float, text: str, font_size: int = 10,
              bold: bool = False, align: str = "left") -> None:
        """Menambahkan teks ke halaman saat ini."""
        font = "/F2" if bold else "/F1"
        # Escape karakter khusus PDF
        safe_text = (text.replace("\\", "\\\\")
                         .replace("(", "\\(")
                         .replace(")", "\\)"))

        if align == "center":
            # Perkiraan lebar teks (kasar)
            text_width = len(text) * font_size * 0.45
            x = (self.page_width - text_width) / 2

        self._current_stream += (
            f"BT\n"
            f"{font} {font_size} Tf\n"
            f"{x:.2f} {y:.2f} Td\n"
            f"({safe_text}) Tj\n"
            f"ET\n"
        ).encode("latin-1", errors="replace")

    def _line(self, x1: float, y1: float, x2: float, y2: float,
              width: float = 1.0) -> None:
        """Menggambar garis."""
        self._current_stream += (
            f"{width:.2f} w\n"
            f"{x1:.2f} {y1:.2f} m\n"
            f"{x2:.2f} {y2:.2f} l\n"
            f"S\n"
        ).encode("latin-1")

    def _rect(self, x: float, y: float, w: float, h: float,
              fill: bool = False, stroke: bool = True,
              fill_gray: float = 0.9) -> None:
        """Menggambar persegi panjang."""
        ops = ""
        if fill:
            ops += f"{fill_gray:.2f} g\n"
        ops += f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re\n"
        if fill and stroke:
            ops += "B\n"
        elif fill:
            ops += "f\n"
        elif stroke:
            ops += "S\n"
        self._current_stream += ops.encode("latin-1")

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
        offsets.append(len(output))
        output += obj_catalog

        # Obj 2: Pages (placeholder, akan diisi nanti)
        pages_placeholder_offset = len(output)

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

        # Build page content streams
        page_obj_ids = []
        stream_obj_ids = []
        next_obj_id = 6

        for content in self.page_contents:
            # Stream object
            stream_id = next_obj_id
            next_obj_id += 1
            stream_obj_ids.append(stream_id)

            # Page object
            page_id = next_obj_id
            next_obj_id += 1
            page_obj_ids.append(page_id)

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
# GENERATOR SERTIFIKAT MUTU BERAS
# ============================================================================

def generate_certificate(
    result: Dict[str, Any],
    output_dir: str = "output",
) -> str:
    """
    Menghasilkan sertifikat mutu beras dalam format PDF A4.

    Parameter
    ---------
    result : dict
        Hasil evaluasi dari evaluate_sample() di quality_engine.py.
    output_dir : str
        Direktori keluaran (default: output/).

    Returns
    -------
    str
        Jalur absolut berkas PDF yang dihasilkan.
    """
    os.makedirs(output_dir, exist_ok=True)

    pdf = PDFWriter()
    pw = pdf.page_width
    ml = pdf.margin_left
    usable_width = pw - ml - pdf.margin_right

    # Posisi Y dimulai dari atas (PDF coordinates: bottom-left origin)
    y = pdf.page_height - pdf.margin_top

    # Ekstrak data dari result
    nomor_sertifikat = result.get("nomor_sertifikat", "N/A")
    sample_id = result.get("sample_id", "N/A")
    tanggal_uji = result.get("tanggal_uji", datetime.now().strftime("%d-%m-%Y %H:%M"))

    params = result.get("parameter_uji", {})
    ka = params.get("kadar_air", 0)
    bp = params.get("butir_patah", 0)
    mn = params.get("butir_menir", 0)
    ba = params.get("benda_asing", 0)

    klasifikasi = result.get("klasifikasi", {})
    kelas = klasifikasi.get("kelas_mutu", "N/A")
    label = klasifikasi.get("label_mutu", "N/A")

    harga = result.get("rekomendasi_harga", {})
    harga_dasar = harga.get("harga_dasar", 0)
    penalti = harga.get("penalti_pengeringan", 0)
    penyusutan = harga.get("potongan_penyusutan", 0)
    harga_bersih = harga.get("harga_bersih", 0)

    # === HEADER ===
    pdf._text(ml, y, "SERTIFIKAT MUTU BERAS", font_size=20, bold=True, align="center")
    y -= 25
    pdf._text(ml, y, "Berdasarkan SNI 6128:2020 & Peraturan Bapanas No. 67/2024",
              font_size=10, align="center")
    y -= 20

    # Garis pemisah tebal
    pdf._line(ml, y, pw - pdf.margin_right, y, width=2.0)
    y -= 25

    # === INFO SERTIFIKAT ===
    pdf._text(ml, y, "INFORMASI SERTIFIKAT", font_size=12, bold=True)
    y -= 18

    info_items = [
        ("Nomor Sertifikat", nomor_sertifikat),
        ("Tanggal Pengujian", tanggal_uji),
        ("Identitas Sampel", sample_id),
    ]
    for label_info, value_info in info_items:
        pdf._text(ml + 10, y, f"{label_info}:", font_size=10, bold=True)
        pdf._text(ml + 180, y, str(value_info), font_size=10)
        y -= 16

    y -= 10
    pdf._line(ml, y, pw - pdf.margin_right, y, width=0.5)
    y -= 20

    # === TABEL PARAMETER MUTU ===
    pdf._text(ml, y, "HASIL PENGUJIAN PARAMETER FISIK", font_size=12, bold=True)
    y -= 20

    # Header tabel
    col_widths = [140, 70, 80, 80, 80]
    headers = ["Parameter", "Nilai Uji", "Batas Premium", "Batas Med. I", "Batas Med. II"]

    # Background header
    pdf._rect(ml, y - 4, usable_width + 55, 18, fill=True, fill_gray=0.85)

    x = ml
    for i, header in enumerate(headers):
        pdf._text(x + 5, y, header, font_size=8, bold=True)
        x += col_widths[i]
    y -= 18

    # Baris data
    rows = [
        ("Kadar Air (%)", f"{ka:.2f}", "14.00", "14.00", "14.00"),
        ("Butir Patah (%)", f"{bp:.2f}", "15.00", "20.00", "25.00"),
        ("Butir Menir (%)", f"{mn:.2f}", "0.50", "2.00", "5.00"),
        ("Benda Asing (%)", f"{ba:.4f}", "0.0100", "0.0200", "0.0500"),
    ]

    for row_idx, row in enumerate(rows):
        if row_idx % 2 == 0:
            pdf._rect(ml, y - 4, usable_width + 55, 16, fill=True, fill_gray=0.95)
        x = ml
        for i, cell in enumerate(row):
            pdf._text(x + 5, y, cell, font_size=9)
            x += col_widths[i]
        y -= 16

    y -= 15
    pdf._line(ml, y, pw - pdf.margin_right, y, width=0.5)
    y -= 25

    # === KELAS MUTU (Box besar) ===
    box_height = 45
    pdf._rect(ml, y - box_height + 20, usable_width + 55, box_height,
              fill=True, stroke=True, fill_gray=0.92)
    pdf._text(ml, y + 5, "KELAS MUTU BERAS:", font_size=12, bold=True, align="center")
    pdf._text(ml, y - 18, label.upper(), font_size=22, bold=True, align="center")
    y -= box_height + 10

    # === REKOMENDASI HARGA ===
    pdf._text(ml, y, "REKOMENDASI HARGA (Bapanas No. 67/2024)", font_size=12, bold=True)
    y -= 20

    harga_items = [
        ("Harga Acuan Bapanas", f"Rp {harga_dasar:,.0f}/kg"),
        ("Potongan Penalti Kadar Air", f"Rp {penalti:,.0f}/kg"),
        ("Potongan Penyusutan Berat", f"Rp {penyusutan:,.0f}/kg"),
    ]
    for lbl, val in harga_items:
        pdf._text(ml + 10, y, f"{lbl}:", font_size=10)
        pdf._text(ml + 280, y, val, font_size=10)
        y -= 16

    # Garis pemisah
    y -= 3
    pdf._line(ml + 10, y, pw - pdf.margin_right, y, width=1.0)
    y -= 18

    pdf._rect(ml + 10, y - 5, usable_width + 35, 22, fill=True, fill_gray=0.9)
    pdf._text(ml + 10, y, "HARGA BERSIH REKOMENDASI:", font_size=11, bold=True)
    pdf._text(ml + 280, y, f"Rp {harga_bersih:,.0f}/kg", font_size=12, bold=True)
    y -= 35

    # === FOOTER ===
    pdf._line(ml, y, pw - pdf.margin_right, y, width=1.0)
    y -= 18

    footer_lines = [
        "Dokumen ini dihasilkan secara otomatis oleh Sistem Penilai Mutu Beras SNI 6128:2020.",
        "Berlaku sebagai acuan mutu internal - bukan pengganti sertifikat laboratorium resmi BSN.",
        f"Dicetak pada: {datetime.now().strftime('%d-%m-%Y %H:%M:%S WIB')}",
    ]
    for line in footer_lines:
        pdf._text(ml, y, line, font_size=7)
        y -= 12

    y -= 10
    pdf._text(ml, y, "Referensi: BSN (2020) SNI 6128:2020 | Bapanas No. 67/2024",
              font_size=7, bold=True)
    y -= 12
    pdf._text(ml, y, "Pengembang: Ramadhaan Imanur Rochima (M0124015) - "
              "S1 Matematika FMIPA UNS",
              font_size=7)

    # === BUILD PDF ===
    pdf.finalize_page()
    pdf_bytes = pdf.build()

    # Simpan ke file
    safe_cert_id = nomor_sertifikat.replace("/", "-")
    filename = f"sertifikat_{safe_cert_id}.pdf"
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
    print("  DEMO: Generator Sertifikat Mutu Beras PDF A4")
    print("=" * 60)

    # Evaluasi sampel contoh
    hasil = evaluate_sample(13.5, 14.0, 0.4, 0.008, sample_id="Beras Premium Demo")

    # Generate PDF
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    path = generate_certificate(hasil, output_dir=output_dir)

    print(f"\n  Kelas Mutu  : {hasil['klasifikasi']['label_mutu']}")
    print(f"  No. Sertifikat: {hasil['nomor_sertifikat']}")
    print(f"  Berkas PDF  : {path}")
    print(f"\n  Sertifikat berhasil digenerate!")
    print("=" * 60)
