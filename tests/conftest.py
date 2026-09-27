"""
PhotoRecover Test Configuration and Synthetic Image Fixtures
"""

import pytest
import numpy as np
from PIL import Image
from io import BytesIO


@pytest.fixture
def sample_jpeg_bytes():
    """Generates a small valid JPEG byte sequence."""
    img = Image.new("RGB", (64, 48), color=(255, 100, 50))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes():
    """Generates a small valid PNG byte sequence."""
    img = Image.new("RGB", (32, 32), color=(0, 200, 100))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
