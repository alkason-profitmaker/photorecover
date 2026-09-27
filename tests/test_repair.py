"""
Unit Test: JPEG Truncation Repair
Tests repairing photos missing EOI or truncated scan streams.
"""

from photorecover.repair import JPEGRepairer
from PIL import Image
from io import BytesIO


def test_repair_truncated_jpeg(sample_jpeg_bytes):
    """
    Simulates a camera photo where recording was abruptly interrupted:
    The trailing EOI marker (\xff\xd9) is truncated.
    """
    assert sample_jpeg_bytes.endswith(b'\xff\xd9')
    truncated = sample_jpeg_bytes[:-2]  # Strip EOI marker
    assert not truncated.endswith(b'\xff\xd9')

    # Attempt repair
    repaired_data, was_repaired, meta = JPEGRepairer.attempt_repair(truncated)

    assert was_repaired is True
    assert repaired_data is not None
    assert repaired_data.endswith(b'\xff\xd9')
    assert meta.get("width") == 64
    assert meta.get("height") == 48

    # Assert Pillow can decode the repaired image without crashing
    with Image.open(BytesIO(repaired_data)) as img:
        img.verify()
