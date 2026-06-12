"""
utils/image_utils.py
--------------------
Pure image-processing logic. No Streamlit imports here — this file
only does computation so it can be tested independently.
"""

import hashlib
import base64
import os
from io import BytesIO

import cv2
from PIL import Image


SUPPORTED = (".jpg", ".jpeg", ".png")


def is_supported(filename: str) -> bool:
    """Returns True if the file extension is a supported image type."""
    return filename.lower().endswith(SUPPORTED)


def compute_md5(filepath: str) -> str:
    """
    Reads a file and returns its MD5 hash as a hex string.
    Used for exact duplicate detection — same hash = byte-for-byte identical files.
    """
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def laplacian_variance(filepath: str) -> float:
    """
    Measures how blurry an image is using Laplacian variance.
    - Converts image to grayscale
    - Applies a Laplacian filter (edge detector)
    - Returns the variance of the result

    LOW variance  → image is blurry (few sharp edges)
    HIGH variance → image is sharp (many clear edges)

    Threshold used in this app: score < 30 = blurry
    """
    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 999.0  # Can't read = skip, don't flag
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def analyze_folder(folder_path: str, all_images: list, progress_callback=None):
    """
    Scans every image in the folder and returns two lists:
      - exact_duplicates: [(filename, original_filename), ...]
      - blurry_images:    [(filename, blur_score), ...]

    progress_callback: optional function(float) called with 0.0–1.0
    """
    hashes = {}
    exact_duplicates = []
    blurry_images = []

    for i, filename in enumerate(all_images):
        filepath = os.path.join(folder_path, filename)

        # --- Duplicate check ---
        fh = compute_md5(filepath)
        if fh in hashes:
            exact_duplicates.append((filename, hashes[fh]))
        else:
            hashes[fh] = filename

        # --- Blur check ---
        score = laplacian_variance(filepath)
        if score < 30:
            blurry_images.append((filename, round(score, 2)))

        if progress_callback:
            progress_callback((i + 1) / len(all_images))

    return exact_duplicates, blurry_images


def image_to_base64_thumb(filepath: str) -> str:
    """
    Opens an image, resizes it to 64×64 (thumbnail), and returns
    a base64-encoded JPEG string. Used for inline HTML previews.
    """
    img = Image.open(filepath)
    img.thumbnail((64, 64))
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()
