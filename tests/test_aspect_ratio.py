"""
Unit Test: Aspect Ratio Preservation
Tests that upscaling to 4K or custom resolutions strictly preserves photo aspect ratios without distortion.
"""

import numpy as np
from photorecover.upscaler import AIUpscaler


def test_aspect_ratio_4_to_3():
    """Verify that a 4:3 photograph is not squished into 16:9 when targeting 4K."""
    upscaler = AIUpscaler()

    # Create synthetic 4:3 image (400 x 300)
    img_4_3 = np.zeros((300, 400, 3), dtype=np.uint8)
    img_4_3[:, :] = [120, 80, 200]

    original_aspect = 400 / 300

    # Upscale to 4K (3840 x 2160 bounding envelope)
    result = upscaler.upscale_to_resolution(img_4_3, target_width=3840, target_height=2160, maintain_aspect=True)

    h, w = result.shape[:2]
    result_aspect = w / h

    # Assert aspect ratio matches within 0.01 tolerance
    assert abs(result_aspect - original_aspect) < 0.01, (
        f"Aspect ratio distorted! Original: {original_aspect:.4f}, Result: {result_aspect:.4f} ({w}x{h})"
    )

    # Assert it fits within the 3840x2160 envelope without exceeding it
    assert w <= 3840 and h <= 2160
    assert w == 2880 and h == 2160


def test_aspect_ratio_square_1_to_1():
    """Verify that a square 1:1 image remains square when upscaled."""
    upscaler = AIUpscaler()

    img_square = np.zeros((200, 200, 3), dtype=np.uint8)
    result = upscaler.upscale_to_resolution(img_square, target_width=3840, target_height=2160, maintain_aspect=True)

    h, w = result.shape[:2]
    assert w == h, f"Square image distorted: {w}x{h}"
    assert w == 2160 and h == 2160


def test_aspect_ratio_upscale_to_4k_method():
    """Test AIUpscaler.upscale_to_4k preserves aspect ratio."""
    upscaler = AIUpscaler()
    img_3_2 = np.zeros((200, 300, 3), dtype=np.uint8)  # 3:2 aspect ratio

    result = upscaler.upscale_to_4k(img_3_2)
    h, w = result.shape[:2]
    ratio = w / h

    assert abs(ratio - 1.5) < 0.01, f"3:2 photo distorted to {ratio} ({w}x{h})"
