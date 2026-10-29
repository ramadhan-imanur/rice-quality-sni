#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cv_engine.py — Mesin Analisis Citra Fisik Beras Berbasis Computer Vision
=======================================================================
Mengimplementasikan analisis morfologi butiran beras digital:
1. Segmentasi citra biner adaptif (Otsu Thresholding) pada latar belakang kontras
2. Pemisahan komponen butiran (Connected Component Labeling & Morphological Filter)
3. Ekstraksi fitur geometris invarian-rotasi melalui Tensor Inersia Orde-2:
   - Panjang aksis mayor (Major Axis Length - L)
   - Lebar aksis minor (Minor Axis Width - W)
   - Rasio Aspek (Aspect Ratio L/W)
   - Luas butir (Area) dan estimasi massa proporsional
4. Klasifikasi butiran SNI 6128:2020:
   - Butir Kepala (L >= 0.8 L0)
   - Butir Patah (0.2 L0 <= L < 0.8 L0)
   - Butir Menir (L < 0.2 L0)
   - Benda Asing / Kotoran (Deteksi anomali warna HSV/RGB dan geometri)
5. Pustaka Standar Python + Pillow, NumPy, SciPy (Lokal, cepat, Rp 0 server).

Penulis : Ramadhaan Imanur Rochima (NIM M0124015)
Lisensi  : Proyek Kewirausahaan — S1 Matematika FMIPA UNS
"""

import base64
import io
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw
import scipy.ndimage as ndi


def _otsu_threshold(gray_u8: np.ndarray) -> float:
    """Menghitung ambang batas optimal Otsu pada citra grayscale uint8."""
    flat = gray_u8.ravel()
    hist, _ = np.histogram(flat, bins=256, range=(0, 256))
    hist = hist.astype(float)
    total = flat.size

    current_max = 0.0
    threshold = 128.0
    sum_total = np.dot(np.arange(256), hist)
    sum_b = 0.0
    w_b = 0.0

    for i in range(256):
        w_b += hist[i]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break

        sum_b += i * hist[i]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f

        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > current_max:
            current_max = var_between
            threshold = float(i)

    # Kembalikan ambang batas dengan offset 0.5 agar tidak rancu dengan nilai piksel diskrit
    return threshold + 0.5


def _calculate_inertia_dimensions(mask: np.ndarray) -> Tuple[float, float, float, float]:
    """
    Menghitung panjang mayor (L), lebar minor (W), rasio aspek, dan luas
    menggunakan momen inersia orde-2 (invarian terhadap rotasi).
    """
    y_coords, x_coords = np.nonzero(mask)
    area = len(x_coords)
    if area < 4:
        return 0.0, 0.0, 0.0, 0.0

    cx = float(np.mean(x_coords))
    cy = float(np.mean(y_coords))

    dx = x_coords - cx
    dy = y_coords - cy

    u20 = np.sum(dx ** 2) / area
    u02 = np.sum(dy ** 2) / area
    u11 = np.sum(dx * dy) / area

    diff = u20 - u02
    term = math.sqrt(max(0.0, diff ** 2 + 4.0 * (u11 ** 2)))
    lambda1 = (u20 + u02 + term) / 2.0
    lambda2 = max(0.0, (u20 + u02 - term) / 2.0)

    length = 4.0 * math.sqrt(max(0.0, lambda1))
    width = 4.0 * math.sqrt(max(0.0, lambda2))
    aspect_ratio = (length / width) if width > 0.0 else 1.0

    return length, width, aspect_ratio, float(area)


# Proteksi DoS Memori: Batas piksel dekompresi Pillow (CWE-400 / Decompression Bomb Guard)
Image.MAX_IMAGE_PIXELS = 25_000_000


def analyze_rice_image(
    image_input: Union[str, bytes, Image.Image],
    coin_diameter_mm: Optional[float] = None,
    min_grain_pixels: int = 15,
    max_grain_pixels: int = 8000,
) -> Dict[str, Any]:
    """
    Menganalisis citra beras pada latar belakang gelap untuk menghitung
    parameter fisik Butir Kepala, Butir Patah, Butir Menir, dan Benda Asing.
    """
    # 1. Buka Citra dengan pelindung batas dekompresi
    try:
        if isinstance(image_input, str):
            with Image.open(image_input) as _f:
                img = _f.convert("RGB")
        elif isinstance(image_input, bytes):
            with Image.open(io.BytesIO(image_input)) as _f:
                img = _f.convert("RGB")
        elif isinstance(image_input, Image.Image):
            img = image_input.convert("RGB")
        else:
            raise TypeError("Format masukan citra tidak didukung.")
    except Image.DecompressionBombError:
        return {
            "success": False,
            "error": "Ukuran citra melampaui batas aman dekompresi (Decompression Bomb Protection).",
        }

    # Skala jika gambar terlalu besar (> 1200px) agar responsif
    orig_w, orig_h = img.size
    max_dim = 1200
    if max(orig_w, orig_h) > max_dim:
        scale = max_dim / max(orig_w, orig_h)
        new_w, new_h = int(orig_w * scale), int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

    arr = np.array(img)
    r = arr[:, :, 0].astype(float)
    g = arr[:, :, 1].astype(float)
    b = arr[:, :, 2].astype(float)

    # Grayscale luminansi
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)

    # 2. Segmentasi Ambang Batas
    thresh_val = _otsu_threshold(gray_u8)
    # Latar belakang gelap: beras lebih terang dari ambang
    binary = gray_u8 > int(thresh_val)

    # Morfologi: Pemisahan derau dan butir dengan 8-konektivitas
    struct_elem = ndi.generate_binary_structure(2, 2)
    opened = ndi.binary_opening(binary, structure=np.ones((2, 2)))

    # 3. Labeling Komponen Terhubung
    labeled, num_features = ndi.label(opened, structure=struct_elem)
    slices = ndi.find_objects(labeled)

    grains_raw = []
    grain_lengths = []

    for idx, slc in enumerate(slices):
        if slc is None:
            continue
        patch_mask = (labeled[slc] == (idx + 1))
        area = int(np.sum(patch_mask))

        if area < min_grain_pixels or area > max_grain_pixels:
            continue

        length, width, aspect, _ = _calculate_inertia_dimensions(patch_mask)
        if length <= 0.0 or width <= 0.0:
            continue

        ymin, xmin = slc[0].start, slc[1].start
        ymax, xmax = slc[0].stop, slc[1].stop

        patch_r = r[slc][patch_mask]
        patch_g = g[slc][patch_mask]
        patch_b = b[slc][patch_mask]

        mean_r = float(np.mean(patch_r))
        mean_g = float(np.mean(patch_g))
        mean_b = float(np.mean(patch_b))

        lum = 0.299 * mean_r + 0.587 * mean_g + 0.114 * mean_b
        color_diff = max(abs(mean_r - mean_g), abs(mean_g - mean_b), abs(mean_r - mean_b))
        is_foreign = (lum < 55.0) or (color_diff > 35.0 and lum < 140.0)

        grains_raw.append({
            "bbox": (xmin, ymin, xmax, ymax),
            "area": area,
            "length": length,
            "width": width,
            "aspect_ratio": aspect,
            "is_foreign": is_foreign,
        })

        if not is_foreign and aspect > 1.3:
            grain_lengths.append(length)

    total_detected = len(grains_raw)
    if total_detected == 0:
        return {
            "success": False,
            "error": "Tidak ada butiran beras yang terdeteksi. Pastikan sampel beras diletakkan merata di atas latar belakang kontras gelap.",
        }

    # 4. Tentukan Standar Panjang Butir Utuh (L0)
    if len(grain_lengths) >= 5:
        l0_ref = float(np.percentile(grain_lengths, 80))
    elif len(grain_lengths) > 0:
        l0_ref = float(np.max(grain_lengths))
    else:
        l0_ref = 30.0

    # 5. Klasifikasi Butiran (SNI 6128:2020)
    count_head = 0
    count_broken = 0
    count_menir = 0
    count_foreign = 0

    area_head = 0.0
    area_broken = 0.0
    area_menir = 0.0
    area_foreign = 0.0

    classified_grains = []
    for g_info in grains_raw:
        length = g_info["length"]
        area = float(g_info["area"])

        if g_info["is_foreign"]:
            kategori = "BENDA_ASING"
            color = (180, 80, 220)  # Ungu
            count_foreign += 1
            area_foreign += area
        elif length >= 0.8 * l0_ref:
            kategori = "BUTIR_KEPALA"
            color = (34, 197, 94)    # Hijau
            count_head += 1
            area_head += area
        elif length >= 0.2 * l0_ref:
            kategori = "BUTIR_PATAH"
            color = (245, 158, 11)   # Kuning / Oranye
            count_broken += 1
            area_broken += area
        else:
            kategori = "BUTIR_MENIR"
            color = (239, 68, 68)    # Merah
            count_menir += 1
            area_menir += area

        g_info["kategori"] = kategori
        g_info["color"] = color
        classified_grains.append(g_info)

    total_rice_area = max(1.0, area_head + area_broken + area_menir)
    total_sample_area = total_rice_area + area_foreign

    pct_head = round((area_head / total_rice_area) * 100.0, 2)
    pct_broken = round((area_broken / total_rice_area) * 100.0, 2)
    pct_menir = round((area_menir / total_rice_area) * 100.0, 2)
    pct_foreign = round((area_foreign / total_sample_area) * 100.0, 4)

    # 6. Gambar Anotasi Hasil Deteksi
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)

    for g_info in classified_grains:
        xmin, ymin, xmax, ymax = g_info["bbox"]
        c = g_info["color"]
        draw.rectangle([xmin, ymin, xmax, ymax], outline=c, width=2)

    buffer = io.BytesIO()
    annotated.save(buffer, format="JPEG", quality=82)
    annotated_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    all_lengths = [g["length"] for g in classified_grains if not g["is_foreign"]]
    all_widths = [g["width"] for g in classified_grains if not g["is_foreign"]]
    avg_l = float(np.mean(all_lengths)) if all_lengths else 0.0
    avg_w = float(np.mean(all_widths)) if all_widths else 0.0

    return {
        "success": True,
        "total_grains": total_detected,
        "l0_reference_px": round(l0_ref, 2),
        "parameter_terukur": {
            "butir_kepala_pct": pct_head,
            "butir_patah_pct": pct_broken,
            "butir_menir_pct": pct_menir,
            "benda_asing_pct": pct_foreign,
        },
        "rincian_jumlah": {
            "butir_kepala": count_head,
            "butir_patah": count_broken,
            "butir_menir": count_menir,
            "benda_asing": count_foreign,
        },
        "morfologi": {
            "rerata_panjang_px": round(avg_l, 2),
            "rerata_lebar_px": round(avg_w, 2),
            "rasio_panjang_lebar": round(avg_l / avg_w, 2) if avg_w > 0 else 0.0,
        },
        "annotated_image_base64": f"data:image/jpeg;base64,{annotated_b64}",
        "classified_grains": classified_grains,
    }


def generate_synthetic_rice_image(
    num_grains: int = 70,
    broken_ratio: float = 0.16,
    menir_ratio: float = 0.02,
    foreign_ratio: float = 0.005,
    width: int = 800,
    height: int = 600,
) -> Image.Image:
    """
    Menghasilkan citra sintetis butiran beras acak di atas baki gelap
    untuk keperluan demonstrasi instan dan pengujian unit otomatis.
    """
    img = Image.new("RGB", (width, height), color=(25, 27, 32))
    draw = ImageDraw.Draw(img)

    np.random.seed(12345)
    for _ in range(num_grains):
        cx = np.random.randint(40, width - 40)
        cy = np.random.randint(40, height - 40)
        rand_type = np.random.rand()

        if rand_type < foreign_ratio:
            s = np.random.randint(3, 7)
            draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=(80, 50, 30))
        elif rand_type < (foreign_ratio + menir_ratio):
            draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(235, 235, 240))
        elif rand_type < (foreign_ratio + menir_ratio + broken_ratio):
            draw.ellipse([cx - 7, cy - 4, cx + 7, cy + 4], fill=(240, 240, 245))
        else:
            draw.ellipse([cx - 14, cy - 4, cx + 14, cy + 4], fill=(245, 245, 250))

    return img


class RiceCVEngine:
    """
    Wrapper berorientasi objek untuk mesin Computer Vision analisis beras.
    Memudahkan pengujian otomatis dan integrasi modular.
    """

    def __init__(self, min_grain_area: int = 15, max_grain_area: int = 8000):
        self.min_grain_pixels = min_grain_area
        self.max_grain_pixels = max_grain_area

    def analyze_image(self, img: Image.Image) -> Dict[str, Any]:
        raw = analyze_rice_image(
            img,
            min_grain_pixels=self.min_grain_pixels,
            max_grain_pixels=self.max_grain_pixels,
        )
        if not raw.get("success", False):
            return {
                "grain_count": 0,
                "butir_kepala": 0,
                "butir_patah": 0,
                "butir_menir": 0,
                "benda_asing": 0,
                "persentase_butir_kepala": 0.0,
                "persentase_butir_patah": 0.0,
                "persentase_butir_menir": 0.0,
                "persentase_benda_asing": 0.0,
                "reference_L0_px": 0.0,
                "details": [],
            }
        p = raw["parameter_terukur"]
        rj = raw["rincian_jumlah"]
        return {
            "grain_count": raw["total_grains"],
            "butir_kepala": rj["butir_kepala"],
            "butir_patah": rj["butir_patah"],
            "butir_menir": rj["butir_menir"],
            "benda_asing": rj["benda_asing"],
            "persentase_butir_kepala": p["butir_kepala_pct"],
            "persentase_butir_patah": p["butir_patah_pct"],
            "persentase_butir_menir": p["butir_menir_pct"],
            "persentase_benda_asing": p["benda_asing_pct"],
            "reference_L0_px": raw["l0_reference_px"],
            "details": raw.get("classified_grains", []),
        }

    def annotate_image(self, img: Image.Image, details: Optional[List[Dict[str, Any]]] = None) -> str:
        raw = analyze_rice_image(
            img,
            min_grain_pixels=self.min_grain_pixels,
            max_grain_pixels=self.max_grain_pixels,
        )
        b64 = raw.get("annotated_image_base64", "")
        if b64.startswith("data:image/jpeg;base64,"):
            b64 = b64.split(",", 1)[1]
        return b64

    def _extract_grain_properties(self, mask: np.ndarray, rgb_arr: Optional[np.ndarray] = None) -> Dict[str, Any]:
        length, width, aspect, area = _calculate_inertia_dimensions(mask)
        return {
            "major_axis_length": length,
            "minor_axis_length": width,
            "aspect_ratio": aspect,
            "area": area,
        }



if __name__ == "__main__":
    print("=" * 60)
    print("  DEMO: Engine Computer Vision Analisis Fisik Beras")
    print("=" * 60)

    synth_img = generate_synthetic_rice_image(num_grains=80)
    res = analyze_rice_image(synth_img)

    print(f"  Total Butir Terdeteksi: {res['total_grains']}")
    p = res["parameter_terukur"]
    print(f"  Butir Kepala  : {p['butir_kepala_pct']}% ({res['rincian_jumlah']['butir_kepala']} butir)")
    print(f"  Butir Patah   : {p['butir_patah_pct']}% ({res['rincian_jumlah']['butir_patah']} butir)")
    print(f"  Butir Menir   : {p['butir_menir_pct']}% ({res['rincian_jumlah']['butir_menir']} butir)")
    print(f"  Benda Asing   : {p['benda_asing_pct']}% ({res['rincian_jumlah']['benda_asing']} partikel)")
    print("=" * 60)
