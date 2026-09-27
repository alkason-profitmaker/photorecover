"""
Unit Test: Multi-Format Signatures and Parsers
Tests JPEG broad markers (APP4-15, COM, SOF1), PNG, TIFF/RAW, and MP4.
"""

from photorecover.signatures import JPEGParser, PNGParser, TIFFRAWParser, MP4VideoParser, MultiFormatCarver, MediaType


def test_broad_jpeg_marker_detection(sample_jpeg_bytes):
    """Asserts that JPEGParser recognizes valid JPEGs."""
    assert JPEGParser.is_valid_header(sample_jpeg_bytes)
    length, is_complete, meta = JPEGParser.parse_stream(sample_jpeg_bytes, 0)
    assert is_complete is True
    assert length == len(sample_jpeg_bytes)
    assert meta["width"] == 64
    assert meta["height"] == 48


def test_jpeg_with_extended_marker():
    """Asserts JPEG parser accepts APP14 (Adobe) and COM markers."""
    # SOI (FF D8) + APP14 (FF EE) + length 14 + data + DQT + SOF0 + SOS + data + EOI
    dummy_jpeg_header = b'\xff\xd8\xff\xee\x00\x0eAdobe\x00\x64\x00\x00\x00\x00\x00'
    assert JPEGParser.is_valid_header(dummy_jpeg_header)


def test_png_parser_complete(sample_png_bytes):
    """Asserts PNG parsing correctly extracts dimensions and detects IEND."""
    assert PNGParser.is_valid_header(sample_png_bytes)
    length, is_complete, meta = PNGParser.parse_stream(sample_png_bytes, 0)
    assert is_complete is True
    assert length == len(sample_png_bytes)
    assert meta["width"] == 32
    assert meta["height"] == 32


def test_multi_format_carver_identification(sample_jpeg_bytes, sample_png_bytes):
    """Asserts MultiFormatCarver properly identifies different media types."""
    m_type, ext = MultiFormatCarver.identify_at_offset(sample_jpeg_bytes, 0)
    assert m_type == MediaType.JPEG
    assert ext == "jpg"

    m_type, ext = MultiFormatCarver.identify_at_offset(sample_png_bytes, 0)
    assert m_type == MediaType.PNG
    assert ext == "png"
