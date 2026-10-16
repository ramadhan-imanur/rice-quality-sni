#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_engine.py — Mesin Klasifikasi Mutu Beras Deterministik SNI 6128:2020
==============================================================================

Modul inti aplikasi Penilai Mutu Beras yang mengimplementasikan:
1. Validasi masukan 4 parameter fisik beras
2. Klasifikasi mutu deterministik O(1) berdasarkan SNI 6128:2020
3. Kalkulasi penyesuaian harga acuan Bapanas No. 67/2024
4. Penyimpanan riwayat pengujian lokal (JSON)

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Referensi: BSN (2020) SNI 6128:2020, Bapanas No. 67/2024
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# KONSTANTA STANDAR SNI 6128:2020 & BAPANAS NO. 67/2024
# ============================================================================

@dataclass(frozen=True)
class BatasTolerasi:
    """Batas toleransi mutu fisik beras per kelas mutu SNI 6128:2020."""
    nama_kelas: str
    label: str
    kadar_air_maks: float      # % (maks)
    butir_patah_maks: float    # % (maks)
    butir_menir_maks: float    # % (maks)
    benda_asing_maks: float    # % (maks)


# Tabel Toleransi Baku SNI 6128:2020 (urutan evaluasi: Premium → Medium I → Medium II)
KELAS_MUTU = [
    BatasTolerasi(
        nama_kelas="PREMIUM",
        label="Premium",
        kadar_air_maks=14.0,
        butir_patah_maks=15.0,
        butir_menir_maks=0.5,
        benda_asing_maks=0.01,
    ),
    BatasTolerasi(
        nama_kelas="MEDIUM_I",
        label="Medium I",
        kadar_air_maks=14.0,
        butir_patah_maks=20.0,
        butir_menir_maks=2.0,
        benda_asing_maks=0.02,
    ),
    BatasTolerasi(
        nama_kelas="MEDIUM_II",
        label="Medium II",
        kadar_air_maks=14.0,
        butir_patah_maks=25.0,
        butir_menir_maks=5.0,
        benda_asing_maks=0.05,
    ),
]

KELAS_SUBSTANDAR = BatasTolerasi(
    nama_kelas="SUBSTANDAR",
    label="Substandar",
    kadar_air_maks=99.0,
    butir_patah_maks=100.0,
    butir_menir_maks=100.0,
    benda_asing_maks=100.0,
)

# Harga Acuan Resmi Bapanas No. 67/2024 (Rp per kg)
HARGA_ACUAN = {
    "HET_PREMIUM": 15_800,   # Harga Eceran Tertinggi beras Premium
    "HET_MEDIUM": 13_500,    # Harga Eceran Tertinggi beras Medium
    "HPP_BERAS": 11_500,     # Harga Pembelian Pemerintah beras
    "HPP_GKG": 7_300,        # Harga Pembelian Pemerintah Gabah Kering Giling
    "HPP_GKP": 6_500,        # Harga Pembelian Pemerintah Gabah Kering Panen
}

# Harga dasar per kelas mutu (Rp/kg)
HARGA_DASAR_PER_KELAS = {
    "PREMIUM": HARGA_ACUAN["HET_PREMIUM"],    # 15.800
    "MEDIUM_I": HARGA_ACUAN["HET_MEDIUM"],    # 13.500
    "MEDIUM_II": HARGA_ACUAN["HET_MEDIUM"],   # 13.500
    "SUBSTANDAR": HARGA_ACUAN["HPP_BERAS"],   # 11.500
}

# Biaya pengeringan per 1% kelebihan kadar air di atas 14% (Rp/kg)
BIAYA_PENGERINGAN_PER_PERSEN = 150

# Penyusutan berat per 1% kelebihan kadar air (1.5% dari harga dasar)
FAKTOR_PENYUSUTAN_PER_PERSEN = 0.015

# Rentang validasi masukan
RENTANG_VALID = {
    "kadar_air": (0.0, 40.0),
    "butir_patah": (0.0, 100.0),
    "butir_menir": (0.0, 100.0),
    "benda_asing": (0.0, 10.0),
}

NAMA_PARAMETER = {
    "kadar_air": "Kadar Air",
    "butir_patah": "Butir Patah",
    "butir_menir": "Butir Menir",
    "benda_asing": "Benda Asing / Kotoran",
}


# ============================================================================
# FUNGSI VALIDASI MASUKAN
# ============================================================================

def validate_input(
    kadar_air: Any,
    butir_patah: Any,
    butir_menir: Any,
    benda_asing: Any,
) -> Tuple[float, float, float, float]:
    """
    Memvalidasi dan membersihkan masukan 4 parameter fisik beras.

    Parameter
    ---------
    kadar_air : float atau int
        Persentase kadar air beras (rentang valid: 0.0 – 40.0%).
    butir_patah : float atau int
        Persentase butir patah (rentang valid: 0.0 – 100.0%).
    butir_menir : float atau int
        Persentase butir menir (rentang valid: 0.0 – 100.0%).
    benda_asing : float atau int
        Persentase benda asing/kotoran (rentang valid: 0.0 – 10.0%).

    Returns
    -------
    tuple of float
        Empat parameter yang sudah divalidasi dan dikonversi ke float.

    Raises
    ------
    TypeError
        Jika masukan bukan tipe numerik (int/float).
    ValueError
        Jika nilai di luar rentang yang diizinkan.
    """
    params = {
        "kadar_air": kadar_air,
        "butir_patah": butir_patah,
        "butir_menir": butir_menir,
        "benda_asing": benda_asing,
    }

    hasil = {}
    for nama, nilai in params.items():
        # Cek tipe data
        if nilai is None:
            raise TypeError(
                f"Parameter '{NAMA_PARAMETER[nama]}' tidak boleh kosong (None)."
            )
        if isinstance(nilai, bool):
            raise TypeError(
                f"Parameter '{NAMA_PARAMETER[nama]}' harus berupa angka, "
                f"bukan boolean."
            )
        if not isinstance(nilai, (int, float)):
            raise TypeError(
                f"Parameter '{NAMA_PARAMETER[nama]}' harus berupa angka numerik, "
                f"diterima tipe '{type(nilai).__name__}'."
            )

        nilai_float = float(nilai)
        batas_min, batas_maks = RENTANG_VALID[nama]

        if nilai_float < batas_min:
            raise ValueError(
                f"Nilai {NAMA_PARAMETER[nama]} ({nilai_float}%) tidak valid: "
                f"tidak boleh negatif (batas minimum {batas_min}%)."
            )
        if nilai_float > batas_maks:
            raise ValueError(
                f"Nilai {NAMA_PARAMETER[nama]} ({nilai_float}%) melebihi "
                f"batas maksimum yang masuk akal ({batas_maks}%)."
            )

        hasil[nama] = nilai_float

    return (
        hasil["kadar_air"],
        hasil["butir_patah"],
        hasil["butir_menir"],
        hasil["benda_asing"],
    )


# ============================================================================
# FUNGSI KLASIFIKASI MUTU SNI 6128:2020
# ============================================================================

def classify_grade(
    kadar_air: float,
    butir_patah: float,
    butir_menir: float,
    benda_asing: float,
) -> Dict[str, Any]:
    """
    Mengklasifikasikan mutu beras secara deterministik berdasarkan SNI 6128:2020.

    Logika evaluasi bertingkat: Premium → Medium I → Medium II → Substandar.
    Kompleksitas waktu: O(1) — maksimal 3 perbandingan tabel.

    Parameter
    ---------
    kadar_air : float
        Persentase kadar air beras.
    butir_patah : float
        Persentase butir patah.
    butir_menir : float
        Persentase butir menir.
    benda_asing : float
        Persentase benda asing / kotoran.

    Returns
    -------
    dict
        Kamus berisi kelas mutu, label, parameter, deviasi, dan stempel waktu.
    """
    # Validasi masukan
    ka, bp, mn, ba = validate_input(kadar_air, butir_patah, butir_menir, benda_asing)

    parameter_uji = {
        "kadar_air": ka,
        "butir_patah": bp,
        "butir_menir": mn,
        "benda_asing": ba,
    }

    # Evaluasi bertingkat deterministik
    kelas_terpilih = KELAS_SUBSTANDAR

    for kelas in KELAS_MUTU:
        if (
            ka <= kelas.kadar_air_maks
            and bp <= kelas.butir_patah_maks
            and mn <= kelas.butir_menir_maks
            and ba <= kelas.benda_asing_maks
        ):
            kelas_terpilih = kelas
            break

    # Hitung deviasi terhadap batas toleransi kelas terpilih
    deviasi = []
    batas_ref = kelas_terpilih if kelas_terpilih != KELAS_SUBSTANDAR else KELAS_MUTU[-1]

    pemetaan_batas = {
        "kadar_air": ("Kadar Air", ka, batas_ref.kadar_air_maks),
        "butir_patah": ("Butir Patah", bp, batas_ref.butir_patah_maks),
        "butir_menir": ("Butir Menir", mn, batas_ref.butir_menir_maks),
        "benda_asing": ("Benda Asing", ba, batas_ref.benda_asing_maks),
    }

    for param_key, (nama, nilai, batas) in pemetaan_batas.items():
        if nilai > batas:
            deviasi.append({
                "parameter": nama,
                "nilai_uji": nilai,
                "batas_toleransi": batas,
                "kelebihan": round(nilai - batas, 4),
            })

    return {
        "kelas_mutu": kelas_terpilih.nama_kelas,
        "label_mutu": kelas_terpilih.label,
        "parameter_uji": parameter_uji,
        "batas_toleransi": {
            "kadar_air_maks": kelas_terpilih.kadar_air_maks,
            "butir_patah_maks": kelas_terpilih.butir_patah_maks,
            "butir_menir_maks": kelas_terpilih.butir_menir_maks,
            "benda_asing_maks": kelas_terpilih.benda_asing_maks,
        },
        "deviasi": deviasi,
        "stempel_waktu": datetime.now().isoformat(),
    }


# ============================================================================
# FUNGSI KALKULASI HARGA — BAPANAS NO. 67/2024
# ============================================================================

def calculate_price(kadar_air: float, grade: str) -> Dict[str, Any]:
    """
    Menghitung rekomendasi harga beli bersih dan potongan penalti wajar.

    Mengacu pada harga acuan resmi Bapanas No. 67/2024:
    - Penalti kadar air: Rp 150/kg per 1% kelebihan di atas 14%
    - Penyusutan berat: 1.5% dari harga dasar per 1% kelebihan kadar air

    Parameter
    ---------
    kadar_air : float
        Persentase kadar air beras.
    grade : str
        Kelas mutu hasil klasifikasi (PREMIUM, MEDIUM_I, MEDIUM_II, SUBSTANDAR).

    Returns
    -------
    dict
        Kamus berisi rincian harga dasar, penalti, penyusutan, dan harga bersih.
    """
    harga_dasar = HARGA_DASAR_PER_KELAS.get(grade, HARGA_ACUAN["HPP_BERAS"])

    # Penalti kadar air jika melebihi 14.0%
    kelebihan_air = max(0.0, kadar_air - 14.0)

    penalti_pengeringan = round(kelebihan_air * BIAYA_PENGERINGAN_PER_PERSEN, 2)
    potongan_penyusutan = round(
        kelebihan_air * FAKTOR_PENYUSUTAN_PER_PERSEN * harga_dasar, 2
    )

    harga_bersih = round(harga_dasar - penalti_pengeringan - potongan_penyusutan, 2)
    harga_bersih = max(0.0, harga_bersih)  # Jangan negatif

    rincian_penalti = []
    if kelebihan_air > 0:
        rincian_penalti.append(
            f"Kelebihan kadar air {kelebihan_air:.1f}%: "
            f"biaya pengeringan Rp {penalti_pengeringan:,.0f}/kg"
        )
        rincian_penalti.append(
            f"Penyusutan berat {kelebihan_air:.1f}% × 1.5% × "
            f"Rp {harga_dasar:,}: Rp {potongan_penyusutan:,.0f}/kg"
        )

    return {
        "harga_dasar": harga_dasar,
        "kelebihan_kadar_air": round(kelebihan_air, 2),
        "penalti_pengeringan": penalti_pengeringan,
        "potongan_penyusutan": potongan_penyusutan,
        "total_potongan": round(penalti_pengeringan + potongan_penyusutan, 2),
        "harga_bersih": harga_bersih,
        "rincian_penalti": rincian_penalti,
    }


# ============================================================================
# FUNGSI EVALUASI SAMPEL TERPADU
# ============================================================================

def evaluate_sample(
    kadar_air: float,
    butir_patah: float,
    butir_menir: float,
    benda_asing: float,
    sample_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mengevaluasi sampel beras secara menyeluruh: validasi, klasifikasi, dan harga.

    Menggabungkan validate_input(), classify_grade(), dan calculate_price()
    menjadi satu panggilan terpadu. Menghasilkan nomor sertifikat unik.

    Parameter
    ---------
    kadar_air : float
        Persentase kadar air.
    butir_patah : float
        Persentase butir patah.
    butir_menir : float
        Persentase butir menir.
    benda_asing : float
        Persentase benda asing.
    sample_id : str, opsional
        Identitas/nama sampel beras (default: otomatis).

    Returns
    -------
    dict
        Kamus lengkap hasil evaluasi untuk sertifikat dan riwayat.
    """
    # Validasi
    ka, bp, mn, ba = validate_input(kadar_air, butir_patah, butir_menir, benda_asing)

    # Klasifikasi
    hasil_klasifikasi = classify_grade(ka, bp, mn, ba)

    # Kalkulasi harga
    grade = hasil_klasifikasi["kelas_mutu"]
    hasil_harga = calculate_price(ka, grade)

    # Nomor dokumen taksasi unik (TKS-YYYYMMDD-XXXXXX)
    tanggal_str = datetime.now().strftime("%Y%m%d")
    kode_unik = uuid.uuid4().hex[:6].upper()
    nomor_taksasi = f"TKS-{tanggal_str}-{kode_unik}"

    if sample_id is None:
        sample_id = f"SAMPEL-{kode_unik}"

    return {
        "nomor_taksasi": nomor_taksasi,
        "nomor_sertifikat": nomor_taksasi,  # Kompatibilitas mundur
        "sample_id": sample_id,
        "tanggal_uji": datetime.now().strftime("%d %B %Y, %H:%M:%S WIB"),
        "tanggal_taksasi": datetime.now().strftime("%d %B %Y, %H:%M:%S WIB"),
        "tanggal_iso": datetime.now().isoformat(),
        "parameter_uji": {
            "kadar_air": ka,
            "butir_patah": bp,
            "butir_menir": mn,
            "benda_asing": ba,
        },
        "klasifikasi": {
            "kelas_mutu": grade,
            "label_mutu": hasil_klasifikasi["label_mutu"],
            "batas_toleransi": hasil_klasifikasi["batas_toleransi"],
            "deviasi": hasil_klasifikasi["deviasi"],
        },
        "rekomendasi_harga": hasil_harga,
        "referensi_regulasi": {
            "standar_mutu": "SNI 6128:2020 (BSN)",
            "acuan_harga": "Peraturan Bapanas No. 67/2024",
        },
    }


# ============================================================================
# MANAJEMEN RIWAYAT PENGUJIAN LOKAL
# ============================================================================

def save_result(
    result: Dict[str, Any],
    filepath: str = "data/lab_samples.json",
) -> str:
    """
    Menyimpan hasil evaluasi sampel ke berkas JSON lokal.

    Parameter
    ---------
    result : dict
        Hasil evaluasi dari evaluate_sample().
    filepath : str
        Lokasi berkas penyimpanan (default: data/lab_samples.json).

    Returns
    -------
    str
        Jalur absolut berkas yang disimpan.
    """
    # Pastikan direktori ada
    dirpath = os.path.dirname(filepath)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    # Muat data lama jika ada
    riwayat = load_history(filepath)

    # Tambahkan hasil baru
    riwayat.append(result)

    # Simpan
    abs_path = os.path.abspath(filepath)
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(riwayat, f, ensure_ascii=False, indent=2)

    return abs_path


def load_history(filepath: str = "data/lab_samples.json") -> List[Dict[str, Any]]:
    """
    Memuat riwayat pengujian dari berkas JSON lokal.

    Parameter
    ---------
    filepath : str
        Lokasi berkas penyimpanan.

    Returns
    -------
    list of dict
        Daftar hasil evaluasi terdahulu. Kosong jika berkas belum ada.
    """
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        return []

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, IOError):
        return []


# ============================================================================
# DEMO STANDALONE
# ============================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("  DEMO: Mesin Klasifikasi Mutu Beras SNI 6128:2020")
    print("  Bapanas No. 67/2024 — Evaluasi Deterministik O(1)")
    print("=" * 65)

    # Contoh sampel
    contoh = [
        ("Beras Premium Ideal", 12.5, 8.0, 0.2, 0.005),
        ("Batas Premium Tepat", 14.0, 15.0, 0.5, 0.01),
        ("Medium I Tipikal", 13.8, 18.0, 1.5, 0.015),
        ("Substandar Basah", 18.0, 12.0, 0.3, 0.008),
    ]

    for nama, ka, bp, mn, ba in contoh:
        print(f"\n--- {nama} ---")
        hasil = evaluate_sample(ka, bp, mn, ba, sample_id=nama)
        print(f"  Kelas Mutu    : {hasil['klasifikasi']['label_mutu']}")
        print(f"  Harga Dasar   : Rp {hasil['rekomendasi_harga']['harga_dasar']:,}/kg")
        print(f"  Total Potongan: Rp {hasil['rekomendasi_harga']['total_potongan']:,}/kg")
        print(f"  Harga Bersih  : Rp {hasil['rekomendasi_harga']['harga_bersih']:,}/kg")
        print(f"  No. Sertifikat: {hasil['nomor_sertifikat']}")

    print("\n" + "=" * 65)
    print("  Semua evaluasi selesai. Mesin deterministik berjalan.")
    print("=" * 65)
