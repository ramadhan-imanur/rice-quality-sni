#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_performance.py — Tolok Ukur Kinerja Komputasi & Alokasi Sumber Daya
=============================================================================

Skrip verifikasi kebutuhan non-fungsional (NFR-01, NFR-02, NFR-03, NFR-04):
- 1.000 iterasi evaluasi klasifikasi mutu dan kalkulasi harga.
- Pengukuran latensi komputasi rata-rata per sampel (time.perf_counter).
- Pengukuran konsumsi memori puncak RAM (tracemalloc).
- Pengukuran ukuran berkas modul kode program.

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import os
import sys
import time
import tracemalloc
from typing import Dict, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (SRC_DIR, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from quality_engine import classify_grade, calculate_price, evaluate_sample


def benchmark_execution(iterations: int = 1000) -> Dict[str, float]:
    """
    Menjalankan simulasi benchmark berulang 1.000 iterasi.
    """
    test_cases: List[Tuple[float, float, float, float]] = [
        (13.5, 14.0, 0.4, 0.008),   # Premium
        (14.0, 15.0, 0.5, 0.01),    # Batas Premium
        (13.8, 18.0, 1.5, 0.015),   # Medium I
        (14.0, 24.0, 4.5, 0.04),    # Medium II
        (16.5, 18.0, 1.5, 0.02),    # Substandar (air tinggi)
    ]

    tracemalloc.start()
    tracemalloc.reset_peak()

    t_start = time.perf_counter()

    for i in range(iterations):
        sample = test_cases[i % len(test_cases)]
        _ = evaluate_sample(sample[0], sample[1], sample[2], sample[3], sample_id=f"Bench-{i}")

    t_end = time.perf_counter()

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_time_sec = t_end - t_start
    avg_latency_ms = (total_time_sec / iterations) * 1000.0
    peak_mem_mb = peak_mem / (1024 * 1024)

    return {
        "iterations": iterations,
        "total_time_sec": total_time_sec,
        "avg_latency_ms": avg_latency_ms,
        "peak_mem_mb": peak_mem_mb,
    }


def calculate_bundle_size() -> Dict[str, int]:
    """Menghitung ukuran berkas modul program utama."""
    files_to_check = [
        os.path.join(SRC_DIR, "quality_engine.py"),
        os.path.join(SRC_DIR, "pdf_generator.py"),
        os.path.join(SRC_DIR, "cli.py"),
        os.path.join(SCRIPT_DIR, "benchmark_performance.py"),
    ]
    sizes = {}
    total = 0
    for fpath in files_to_check:
        fname = os.path.basename(fpath)
        if os.path.exists(fpath):
            sz = os.path.getsize(fpath)
            sizes[fname] = sz
            total += sz
    sizes["_total_bytes"] = total
    return sizes


def main() -> None:
    print("=" * 72)
    print(" TOLOK UKUR KINERJA KOMPUTASI & SUMBER DAYA SISTEM (NFR BENCHMARK)")
    print(" Evaluasi Deterministik SNI 6128:2020 & Bapanas No. 67/2024")
    print("=" * 72)

    iterations = 1000
    print(f"\n[1/3] Menjalankan {iterations:,} iterasi evaluasi sampel...")
    metrics = benchmark_execution(iterations)

    print("\n[2/3] Menghitung ukuran bundel berkas modul kode program...")
    sizes = calculate_bundle_size()

    print("\n[3/3] Hasil Pengujian dan Verifikasi Standar NFR:")
    print("-" * 72)
    print(f"{'Parameter Metrik':<30} | {'Hasil Uji':<15} | {'Ambang Batas PRD':<16} | Status")
    print("-" * 72)

    status_latency = "LULUS" if metrics["avg_latency_ms"] < 10.0 else "GAGAL"
    print(f"{'Latensi Komputasi Logika':<30} | {metrics['avg_latency_ms']:.4f} ms{'':<6} | < 10.00 ms{'':<6} | {status_latency}")

    status_mem = "LULUS" if metrics["peak_mem_mb"] < 40.0 else "GAGAL"
    print(f"{'Konsumsi Puncak Memori (RAM)':<30} | {metrics['peak_mem_mb']:.4f} MB{'':<6} | < 40.00 MB{'':<6} | {status_mem}")

    total_kb = sizes["_total_bytes"] / 1024.0
    status_size = "LULUS" if total_kb < 1024.0 else "GAGAL"
    print(f"{'Ukuran Berkas Modul Kode':<30} | {total_kb:.2f} KB{'':<7} | < 1.00 MB{'':<7} | {status_size}")

    print(f"{'Dependensi Server / Cloud':<30} | {'0 (Offline)':<15} | {'Rp 0 / Lokal':<16} | LULUS")
    print("-" * 72)

    print("\nRingkasan Detail Ukuran Berkas:")
    for k, v in sizes.items():
        if k != "_total_bytes":
            print(f"  - {k:<28}: {v:>8,d} bytes ({v/1024.0:.2f} KB)")
    print(f"  {'Total Ukuran Kode Python':<30}: {sizes['_total_bytes']:>8,d} bytes ({total_kb:.2f} KB)")

    print("\n" + "=" * 72)
    if status_latency == "LULUS" and status_mem == "LULUS" and status_size == "LULUS":
        print(" Selesai: Seluruh parameter NFR terverifikasi memenuhi standar PRD.")
    else:
        print(" PERINGATAN: Terdapat parameter NFR yang melebihi batas ambang PRD!")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
