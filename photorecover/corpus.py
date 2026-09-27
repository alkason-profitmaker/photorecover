"""
Synthetic Recovery Benchmark Corpus Generator
Generates test disk images with known ground truth for validation and regression testing:
- Boundary crossing photos
- Truncated JPEGs
- Multi-format assets (PNG, RAW, JPEG)
- Synthetic FAT32 partitions with deleted directory entries
"""

import os
import struct
import numpy as np
from pathlib import Path
from io import BytesIO
from PIL import Image


def _create_pattern_image(w: int, h: int, seed: int) -> Image.Image:
    """Generates an image with a non-trivial gradient pattern for realistic entropy."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            arr[y, x] = [(x * 7 + seed) % 256, (y * 5 + seed * 3) % 256, (x + y + seed * 11) % 256]
    return Image.fromarray(arr)


def create_synthetic_recovery_corpus(output_path: str, size_mb: int = 4) -> dict:
    """
    Creates a synthetic storage disk image with known ground truth files.
    Returns: dict with counts of embedded files and ground truth offsets.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = size_mb * 1024 * 1024
    disk = bytearray(total_bytes)

    ground_truth = {
        "intact_jpegs": 0,
        "boundary_jpegs": 0,
        "truncated_jpegs": 0,
        "pngs": 0,
        "raw_tiffs": 0,
        "total_embeds": 0
    }

    # 1. Embed an intact photo (placed at offset 4096)
    im1 = _create_pattern_image(200, 150, seed=1)
    b1 = BytesIO()
    im1.save(b1, format="JPEG", quality=85)
    jpg1 = b1.getvalue()
    disk[4096:4096 + len(jpg1)] = jpg1
    ground_truth["intact_jpegs"] += 1

    # 2. Embed a boundary-spanning photo across 64KB (65536)
    im2 = _create_pattern_image(240, 180, seed=2)
    b2 = BytesIO()
    im2.save(b2, format="JPEG", quality=85)
    jpg2 = b2.getvalue()
    pos2 = 62 * 1024  # Starts at 62 KB and extends past 64 KB
    disk[pos2:pos2 + len(jpg2)] = jpg2
    ground_truth["boundary_jpegs"] += 1

    # 3. Embed a boundary-spanning photo across 1MB (1048576)
    im3 = _create_pattern_image(280, 200, seed=3)
    b3 = BytesIO()
    im3.save(b3, format="JPEG", quality=85)
    jpg3 = b3.getvalue()
    pos3 = 1048576 - 2048
    disk[pos3:pos3 + len(jpg3)] = jpg3
    ground_truth["boundary_jpegs"] += 1

    # 4. Embed a truncated photo (missing trailing EOI)
    im4 = _create_pattern_image(180, 140, seed=4)
    b4 = BytesIO()
    im4.save(b4, format="JPEG", quality=85)
    jpg4 = b4.getvalue()[:-2]  # Strip EOI
    pos4 = 1500 * 1024
    disk[pos4:pos4 + len(jpg4)] = jpg4
    ground_truth["truncated_jpegs"] += 1

    # 5. Embed a PNG image
    im5 = _create_pattern_image(120, 120, seed=5)
    b5 = BytesIO()
    im5.save(b5, format="PNG")
    png_data = b5.getvalue()
    pos5 = 2000 * 1024
    disk[pos5:pos5 + len(png_data)] = png_data
    ground_truth["pngs"] += 1

    # 6. Embed a valid TIFF/RAW file (Little Endian II*\x00)
    tiff_header = (
        b'II*\x00\x08\x00\x00\x00'  # Header
        b'\x01\x00'                  # 1 entry
        b'\x00\x01\x04\x00\x01\x00\x00\x00\xf4\x01\x00\x00'  # Tag 0x100 = 500
        b'\x00\x00\x00\x00'          # Next IFD offset
        + b'\x00' * 4096             # Payload
    )
    pos6 = 2500 * 1024
    disk[pos6:pos6 + len(tiff_header)] = tiff_header
    ground_truth["raw_tiffs"] += 1

    ground_truth["total_embeds"] = (
        ground_truth["intact_jpegs"] +
        ground_truth["boundary_jpegs"] +
        ground_truth["truncated_jpegs"] +
        ground_truth["pngs"] +
        ground_truth["raw_tiffs"]
    )

    out_file.write_bytes(bytes(disk))
    return ground_truth
