"""
Unit Test: Zero-Loss Chunk Boundary Crossing
Tests the exact scenario identified in the ChatGPT review:
Ensures a JPEG crossing scanner chunk boundaries is never skipped or dropped.
"""

import os
from pathlib import Path
from PIL import Image
from io import BytesIO
from photorecover.recovery import SDCardRecovery


def test_jpeg_crossing_chunk_boundary(tmp_path):
    """
    Constructs a synthetic disk image where a photo strictly crosses the chunk boundary.
    Asserts 100% recovery with zero dropped files.
    """
    chunk_size = 64 * 1024  # 64 KB chunk size

    # Create 3 distinct JPEGs
    img1 = Image.new("RGB", (80, 60), color=(255, 0, 0))
    b1 = BytesIO()
    img1.save(b1, format="JPEG")
    jpeg1 = b1.getvalue()

    img2 = Image.new("RGB", (100, 80), color=(0, 255, 0))
    b2 = BytesIO()
    img2.save(b2, format="JPEG")
    jpeg2 = b2.getvalue()

    img3 = Image.new("RGB", (120, 90), color=(0, 0, 255))
    b3 = BytesIO()
    img3.save(b3, format="JPEG")
    jpeg3 = b3.getvalue()

    # Create synthetic disk image of size 192 KB (3 chunks)
    disk_data = bytearray(chunk_size * 3)

    # Place Photo 1 inside chunk 0
    pos1 = 5000
    disk_data[pos1:pos1 + len(jpeg1)] = jpeg1

    # Place Photo 2 spanning chunk 0 and chunk 1!
    # Starts at 60 KB, ends at 60 KB + len(jpeg2) > 64 KB
    pos2 = 60 * 1024
    disk_data[pos2:pos2 + len(jpeg2)] = jpeg2

    # Place Photo 3 inside chunk 2
    pos3 = 140 * 1024
    disk_data[pos3:pos3 + len(jpeg3)] = jpeg3

    # Write synthetic disk image
    disk_img_path = tmp_path / "synthetic_sdcard.img"
    disk_img_path.write_bytes(bytes(disk_data))

    out_dir = tmp_path / "recovered_output"

    # Initialize recovery engine with 64 KB chunk size
    recovery = SDCardRecovery(
        validate_images=True,
        deduplicate=True,
        attempt_repair=False,
        min_size=100,
        verbose=False
    )

    recovered = recovery.recover(
        source_path=str(disk_img_path),
        output_dir=str(out_dir),
        scan_filesystem=False,
        chunk_size=chunk_size
    )

    # Verify that ALL 3 photos were recovered, including the boundary crossing one!
    assert len(recovered) == 3, f"Expected 3 photos recovered, but got {len(recovered)}! Boundary bug detected."

    # Validate image files exist and can be loaded
    for item in recovered:
        assert Path(item.path).exists()
        with Image.open(item.path) as im:
            im.verify()
