#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli.py — Antarmuka Baris Perintah Penilai Mutu Beras SNI 6128:2020
==================================================================

Program CLI interaktif dan non-interaktif untuk:
1. Input 4 parameter fisik beras (Kadar Air, Patah, Menir, Benda Asing).
2. Evaluasi deterministik O(1) kelas mutu SNI 6128:2020.
3. Kalkulasi rekomendasi harga beli bersih Bapanas No. 67/2024.
4. Ekspor lembar sertifikat mutu PDF A4 lokal.
5. Penyimpanan dan penelusuran riwayat pengujian lokal.

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Optional

# Pastikan modul internal terjangkau
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from quality_engine import (
    evaluate_sample,
    save_result,
    load_history,
    RENTANG_VALID,
    NAMA_PARAMETER,
    HARGA_ACUAN,
)
from pdf_generator import generate_certificate


DEFAULT_DATA_PATH = os.path.join(CURRENT_DIR, "data", "lab_samples.json")
DEFAULT_OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")


def print_banner() -> None:
    """Menampilkan kop program."""
    print("=" * 68)
    print(" SISTEM PENILAI MUTU BERAS DETERMINISTIK SNI 6128:2020")
    print(" Acuan Harga: Peraturan Badan Pangan Nasional No. 67/2024")
    print(" S1 Matematika FMIPA Universitas Sebelas Maret (UNS)")
    print("=" * 68)


def prompt_float(nama_param: str, batas_min: float, batas_maks: float) -> float:
    """
    Meminta masukan float dengan validasi batas berulang sampai valid.
    """
    label = NAMA_PARAMETER.get(nama_param, nama_param)
    while True:
        try:
            raw = input(f"  [?] Masukkan {label} (%) [{batas_min:.1f} - {batas_maks:.1f}]: ").strip()
            if not raw:
                print("      Galat: Nilai tidak boleh kosong.")
                continue
            # Ganti koma dengan titik desimal jika dimasukkan format Indonesia
            raw_normalized = raw.replace(",", ".")
            val = float(raw_normalized)
            if val < batas_min:
                print(f"      Galat: Nilai {val}% di bawah batas minimum {batas_min}%.")
                continue
            if val > batas_maks:
                print(f"      Galat: Nilai {val}% melebihi batas maksimum {batas_maks}%.")
                continue
            return val
        except ValueError:
            print("      Galat: Masukan harus berupa angka numerik desimal.")


def display_result(result: dict) -> None:
    """Menampilkan hasil evaluasi secara rapi di terminal."""
    params = result["parameter_uji"]
    klas = result["klasifikasi"]
    harga = result["rekomendasi_harga"]

    print("\n" + "-" * 68)
    print(" HASIL EVALUASI MUTU & REKOMENDASI HARGA")
    print("-" * 68)
    print(f"  Identitas Sampel : {result['sample_id']}")
    print(f"  No. Sertifikat   : {result['nomor_sertifikat']}")
    print(f"  Waktu Pemeriksaan: {result['tanggal_uji']}")
    print("-" * 68)
    print("  PARAMETER FISIK TERUKUR:")
    print(f"    - Kadar Air       : {params['kadar_air']:.2f}% (Batas SNI: <= 14.00%)")
    print(f"    - Butir Patah     : {params['butir_patah']:.2f}%")
    print(f"    - Butir Menir     : {params['butir_menir']:.2f}%")
    print(f"    - Benda Asing     : {params['benda_asing']:.4f}%")
    print("-" * 68)
    print(f"  KELAS MUTU SNI   : >> {klas['label_mutu'].upper()} <<")
    if klas["deviasi"]:
        print("  DEVIASI DARI STANDAR:")
        for d in klas["deviasi"]:
            print(f"    * {d['parameter']}: {d['nilai_uji']}% (toleransi {d['batas_toleransi']}%, selisih +{d['kelebihan']}%)")
    else:
        print("  Status Batas     : Seluruh parameter memenuhi toleransi baku kelas.")
    print("-" * 68)
    print("  KALKULASI HARGA (Bapanas No. 67/2024):")
    print(f"    - Harga Acuan Dasar     : Rp {harga['harga_dasar']:>10,}/kg")
    print(f"    - Penalti Pengeringan   : Rp {harga['penalti_pengeringan']:>10,}/kg")
    print(f"    - Potongan Penyusutan   : Rp {harga['potongan_penyusutan']:>10,}/kg")
    print(f"    - Total Potongan        : Rp {harga['total_potongan']:>10,}/kg")
    print(f"    ------------------------------------------------")
    print(f"    - REKOMENDASI BERSIH    : Rp {harga['harga_bersih']:>10,}/kg")
    print("-" * 68)


def run_interactive() -> None:
    """Menjalankan wizard input bertahap interaktif."""
    print_banner()
    print("\n[LANGKAH 1 DARI 5] Identitas Sampel")
    sample_id = input("  Masukkan Nama / Kode Sampel (tekan Enter untuk default): ").strip()
    if not sample_id:
        sample_id = f"Sampel-{datetime.now().strftime('%H%M%S')}"

    print("\n[LANGKAH 2 DARI 5] Pengukuran 4 Parameter Fisik")
    ka = prompt_float("kadar_air", *RENTANG_VALID["kadar_air"])
    bp = prompt_float("butir_patah", *RENTANG_VALID["butir_patah"])
    mn = prompt_float("butir_menir", *RENTANG_VALID["butir_menir"])
    ba = prompt_float("benda_asing", *RENTANG_VALID["benda_asing"])

    result = evaluate_sample(ka, bp, mn, ba, sample_id=sample_id)
    display_result(result)

    # Simpan riwayat
    print("\n[LANGKAH 3 DARI 5] Penyimpanan Data")
    simpan = input("  Simpan evaluasi ke riwayat lokal (lab_samples.json)? [Y/n]: ").strip().lower()
    if simpan in ("", "y", "ya", "yes"):
        saved_path = save_result(result, filepath=DEFAULT_DATA_PATH)
        print(f"  [+] Data tersimpan di: {saved_path}")

    # Ekspor PDF
    print("\n[LANGKAH 4 DARI 5] Ekspor Sertifikat Mutu Digital")
    cetak_pdf = input("  Cetak lembar sertifikat resmi PDF A4? [Y/n]: ").strip().lower()
    if cetak_pdf in ("", "y", "ya", "yes"):
        pdf_path = generate_certificate(result, output_dir=DEFAULT_OUTPUT_DIR)
        print(f"  [+] Sertifikat PDF berhasil terbit: {pdf_path}")

    print("\n" + "=" * 68)
    print(" Selesai. Pengujian mutu tuntas secara deterministik.")
    print("=" * 68 + "\n")


def view_history() -> None:
    """Menampilkan daftar riwayat evaluasi dari file JSON."""
    history = load_history(DEFAULT_DATA_PATH)
    print_banner()
    print(f"\nRIWAYAT PENGUJIAN SAMPEL ({len(history)} data tersimpan)")
    print("-" * 68)
    if not history:
        print("  Belum ada data riwayat pengujian di lab_samples.json.")
        print("-" * 68)
        return

    print(f"{'No':<3} | {'Tanggal':<19} | {'Sampel ID':<20} | {'Mutu':<10} | {'Harga Bersih':<10}")
    print("-" * 68)
    for idx, item in enumerate(history[-15:], 1):
        tgl = item.get("tanggal_iso", "")[:19].replace("T", " ")
        sid = item.get("sample_id", "N/A")[:20]
        mutu = item.get("klasifikasi", {}).get("label_mutu", "N/A")
        hrg = item.get("rekomendasi_harga", {}).get("harga_bersih", 0)
        print(f"{idx:<3} | {tgl:<19} | {sid:<20} | {mutu:<10} | Rp {hrg:,.0f}")
    print("-" * 68)


def main() -> None:
    """Parser argumen baris perintah."""
    parser = argparse.ArgumentParser(
        description="Evaluasi Mutu Beras SNI 6128:2020 & Acuan Harga Bapanas No. 67/2024"
    )
    parser.add_argument("-i", "--interactive", action="store_true", help="Jalankan mode wizard interaktif")
    parser.add_argument("--ka", "--kadar-air", dest="kadar_air", type=float, help="Kadar Air (persen, misal 13.5)")
    parser.add_argument("--bp", "--butir-patah", dest="butir_patah", type=float, help="Butir Patah (persen, misal 14.0)")
    parser.add_argument("--mn", "--butir-menir", dest="butir_menir", type=float, help="Butir Menir (persen, misal 0.4)")
    parser.add_argument("--ba", "--benda-asing", dest="benda_asing", type=float, help="Benda Asing (persen, misal 0.008)")
    parser.add_argument("--id", "--sample-id", dest="sample_id", type=str, default=None, help="Nama / ID Sampel")
    parser.add_argument("--pdf", action="store_true", help="Hasilkan lembar sertifikat PDF A4 secara otomatis")
    parser.add_argument("--save", action="store_true", help="Simpan hasil evaluasi ke lab_samples.json")
    parser.add_argument("--history", action="store_true", help="Tampilkan riwayat pengujian sampel")

    args = parser.parse_args()

    if args.history:
        view_history()
        return

    # Jika salah satu parameter diberikan via flag
    if any(param is not None for param in [args.kadar_air, args.butir_patah, args.butir_menir, args.benda_asing]):
        if any(param is None for param in [args.kadar_air, args.butir_patah, args.butir_menir, args.benda_asing]):
            print("Galat: Seluruh 4 parameter (--ka, --bp, --mn, --ba) wajib diisi bersamaan.")
            sys.exit(1)

        result = evaluate_sample(
            args.kadar_air,
            args.butir_patah,
            args.butir_menir,
            args.benda_asing,
            sample_id=args.sample_id,
        )
        display_result(result)

        if args.save:
            saved_path = save_result(result, filepath=DEFAULT_DATA_PATH)
            print(f"[+] Hasil tersimpan: {saved_path}")

        if args.pdf:
            pdf_path = generate_certificate(result, output_dir=DEFAULT_OUTPUT_DIR)
            print(f"[+] Sertifikat PDF terbit: {pdf_path}")
        return

    # Default ke mode interaktif
    run_interactive()


if __name__ == "__main__":
    main()
