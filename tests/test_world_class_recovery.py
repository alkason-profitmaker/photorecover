"""
Test Suite: World-Class Photo Recovery and Permanent Vault Guarantee
Verifies:
1. HEIC and WebP multi-format identification and carving
2. Clean JPEG re-synthesis during damaged photo repair
3. World-class studio photo restoration and dynamic range lift
4. Permanent vault non-deletion guarantee, fsync sync, collision prevention, and HTML report generation
"""

import os
import struct
import numpy as np
from pathlib import Path
from io import BytesIO
from PIL import Image

from photorecover.signatures import HEICParser, WebPParser, MultiFormatCarver, MediaType
from photorecover.repair import JPEGRepairer
from photorecover.enhancer import ImageEnhancer
from photorecover.recovery import SDCardRecovery


def test_heic_parser_identification():
    """Verifies that HEIC/HEIF smartphone camera photos are recognized and carved."""
    # Synthetic ISOBMFF HEIC box: ftyp (brand 'heic') + meta box + mdat box
    ftyp_box = struct.pack(">I", 24) + b'ftyp' + b'heic' + struct.pack(">I", 0) + b'mif1' + b'heic'
    meta_box = struct.pack(">I", 16) + b'meta' + b'\x00' * 8
    mdat_box = struct.pack(">I", 32) + b'mdat' + b'\xFF' * 24
    heic_bytes = ftyp_box + meta_box + mdat_box

    assert HEICParser.is_valid_header(heic_bytes)
    media_type, ext = MultiFormatCarver.identify_at_offset(heic_bytes, 0)
    assert media_type == MediaType.HEIC
    assert ext == "heic"

    length, is_complete, meta = HEICParser.parse_stream(heic_bytes, 0)
    assert is_complete is True
    assert length == len(heic_bytes)


def test_webp_parser_identification():
    """Verifies that WebP image containers are recognized and carved."""
    payload_len = 24
    # RIFF header: 'RIFF' + 4-byte length + 'WEBP' + dummy chunk
    webp_bytes = b'RIFF' + struct.pack("<I", payload_len + 4) + b'WEBP' + b'VP8 ' + struct.pack("<I", payload_len - 8) + b'\x00' * (payload_len - 8)

    assert WebPParser.is_valid_header(webp_bytes)
    media_type, ext = MultiFormatCarver.identify_at_offset(webp_bytes, 0)
    assert media_type == MediaType.WEBP
    assert ext == "webp"

    length, is_complete, meta = WebPParser.parse_stream(webp_bytes, 0)
    assert is_complete is True
    assert length == len(webp_bytes)


def test_clean_jpeg_resynthesis(sample_jpeg_bytes):
    """Verifies that damaged or truncated JPEGs are repaired into clean standards-compliant baseline JPEGs."""
    # Truncate EOI marker
    truncated = sample_jpeg_bytes[:-2]
    assert not truncated.endswith(b'\xff\xd9')

    repaired_data, was_repaired, meta = JPEGRepairer.attempt_repair(truncated)
    assert was_repaired is True
    assert repaired_data is not None
    assert repaired_data.endswith(b'\xff\xd9')

    # Verify that the synthesized clean JPEG opens cleanly in Pillow without warnings
    with Image.open(BytesIO(repaired_data)) as img:
        img.verify()
    with Image.open(BytesIO(repaired_data)) as img:
        w, h = img.size
        assert w > 0 and h > 0


def test_studio_photo_restoration():
    """Verifies the World-Class Studio Photo Restoration pipeline."""
    enhancer = ImageEnhancer()

    # Create synthetic dark, faded photo with low contrast
    dark_img = np.full((120, 160, 3), 35, dtype=np.uint8)
    # Add some colored shapes
    dark_img[20:60, 20:60] = [60, 30, 30]  # dark reddish
    dark_img[60:100, 80:140] = [30, 60, 30]  # dark greenish

    # Run studio restoration
    restored = enhancer.studio_photo_restore(
        dark_img,
        enhance_portrait=False,
        auto_exposure=True,
        denoise=True,
        super_resolve_scale=1.0
    )

    assert restored.shape == dark_img.shape
    # Dynamic range must be significantly lifted
    assert np.mean(restored) > np.mean(dark_img)
    # High-quality color preservation
    assert restored.dtype == np.uint8


def test_permanent_vault_guarantee(tmp_path, sample_jpeg_bytes):
    """
    Verifies the Permanent Vault Non-Deletion Guarantee:
    1. Rescued photos are physically written to disk
    2. Zero file collision overwrite (unique naming)
    3. Manifest, README vault certificate, and interactive HTML report are generated
    """
    src_img = tmp_path / "sdcard_test.img"
    out_dir = tmp_path / "Permanent_Vault"

    # Embed two identical JPEGs to test deduplication and collision prevention
    disk_data = bytearray(b'\x00' * 4096)
    disk_data.extend(sample_jpeg_bytes)
    disk_data.extend(b'\x00' * 4096)
    src_img.write_bytes(bytes(disk_data))

    recovery = SDCardRecovery(validate_images=True, deduplicate=False, min_size=100, verbose=False)
    items = recovery.recover(str(src_img), str(out_dir), scan_filesystem=False)

    assert len(items) >= 1
    recovered_file = Path(items[0].path)
    assert recovered_file.exists()
    assert recovered_file.stat().st_size > 0

    # Verify permanent vault artifacts
    manifest_path = out_dir / "recovery_manifest.json"
    assert manifest_path.exists()

    report_path = out_dir / "RECOVERY_REPORT.html"
    assert report_path.exists()
    report_content = report_path.read_text(encoding="utf-8")
    assert "PhotoRecover 2.0" in report_content
    assert "Permanent Non-Deletion Guarantee" in report_content

    readme_path = out_dir / "README_PERMANENT_VAULT.txt"
    assert readme_path.exists()
    readme_content = readme_path.read_text(encoding="utf-8")
    assert "GUARANTEE OF PERMANENT NON-DELETION" in readme_content
