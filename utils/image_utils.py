"""
utils/image_utils.py
--------------------
Pure image-processing logic. No Streamlit imports here.
Works with file paths on disk.
"""

import hashlib
import base64
import os
from io import BytesIO

import cv2
from PIL import Image


SUPPORTED = (".jpg", ".jpeg", ".png")


def is_supported(filename: str) -> bool:
    return filename.lower().endswith(SUPPORTED)


def compute_md5(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def laplacian_variance(filepath: str) -> float:
    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 999.0
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def analyze_folder(folder_path: str, all_images: list, progress_callback=None):
    hashes = {}
    exact_duplicates = []
    blurry_images = []

    for i, filename in enumerate(all_images):
        filepath = os.path.join(folder_path, filename)

        fh = compute_md5(filepath)
        if fh in hashes:
            exact_duplicates.append((filename, hashes[fh]))
        else:
            hashes[fh] = filename

        score = laplacian_variance(filepath)
        if score < 30:
            blurry_images.append((filename, round(score, 2)))

        if progress_callback:
            progress_callback((i + 1) / len(all_images))

    return exact_duplicates, blurry_images


def image_to_base64_thumb(filepath: str) -> str:
    img = Image.open(filepath)
    img.thumbnail((64, 64))
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode()
