"""
Rice Quality Grader & Digital Certificate Engine (SNI 6128:2020)
Package Source Module
"""

from src.quality_engine import (
    KELAS_MUTU,
    KELAS_SUBSTANDAR,
    HARGA_ACUAN,
    evaluate_sample,
    classify_grade,
    calculate_price,
    validate_input,
)
from src.database import get_db_connection, init_db
from src.pdf_generator import generate_certificate, generate_sample_label
from src.cv_engine import analyze_rice_image, generate_synthetic_rice_image
from src.qr_codec import generate_qr_matrix

__version__ = "1.0.0"
__author__ = "Ramadhaan Imanur Rochima (NIM M0124015)"
__all__ = [
    "KELAS_MUTU",
    "KELAS_SUBSTANDAR",
    "HARGA_ACUAN",
    "evaluate_sample",
    "classify_grade",
    "calculate_price",
    "validate_input",
    "get_db_connection",
    "init_db",
    "generate_certificate",
    "generate_sample_label",
    "analyze_rice_image",
    "generate_synthetic_rice_image",
    "generate_qr_matrix",
]
