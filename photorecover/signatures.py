"""
Multi-Format Signatures and Stream Parsers
Supports JPEG (broad markers), PNG, TIFF/RAW (CR2, NEF, ARW, DNG), MP4/MOV, WebP, and GIF.
"""

import struct
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum


class MediaType(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    HEIC = "heic"
    WEBP = "webp"
    TIFF_RAW = "raw_tiff"
    MP4_VIDEO = "video_mp4"
    GIF = "gif"
    UNKNOWN = "unknown"


@dataclass
class CarveCandidate:
    """Represents a carved file candidate identified in a byte stream."""
    media_type: MediaType
    start_offset: int
    size: int
    is_complete: bool
    extension: str
    metadata: Dict[str, Any]


class JPEGParser:
    """Broad JPEG marker detector and structural stream validator."""

    SOI = b'\xff\xd8'
    EOI = b'\xff\xd9'
    SOS = b'\xff\xda'

    # Valid markers following SOI in standards-compliant JPEGs
    VALID_POST_SOI_MARKERS = {
        # APP0 - APP15 (JFIF, EXIF, ICC, Adobe, camera-specific metadata)
        0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7,
        0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF,
        # Quantization table
        0xDB,
        # Start of Frame (Baseline, Extended Sequential, Progressive, Lossless, Differential)
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        # Huffman table
        0xC4,
        # Restart Interval
        0xDD,
        # Comment
        0xFE
    }

    @classmethod
    def is_valid_header(cls, data: bytes, offset: int = 0) -> bool:
        """Check if bytes at offset form a valid JPEG start."""
        if len(data) - offset < 4:
            return False
        if data[offset:offset + 2] != cls.SOI:
            return False
        # Next byte must be 0xFF
        if data[offset + 2] != 0xFF:
            return False
        # Following byte must be a valid JPEG marker
        marker_type = data[offset + 3]
        return marker_type in cls.VALID_POST_SOI_MARKERS

    @classmethod
    def parse_stream(cls, data: bytes, start: int, max_size: int = 50 * 1024 * 1024) -> Tuple[Optional[int], bool, Dict[str, Any]]:
        """
        Parses JPEG structure from start offset.
        Returns: (file_length, is_complete, metadata)
        If EOI is found, returns (length, True, metadata).
        If stream ends before EOI or hits corruption, returns (best_effort_length, False, metadata).
        """
        data_len = len(data)
        limit = min(start + max_size, data_len)
        pos = start + 2  # skip SOI
        metadata: Dict[str, Any] = {"width": None, "height": None, "exif": False, "jfif": False}

        while pos < limit - 1:
            if data[pos] != 0xFF:
                pos += 1
                continue

            # Skip fill bytes (0xFF 0xFF)
            while pos < limit - 1 and data[pos + 1] == 0xFF:
                pos += 1

            if pos >= limit - 1:
                break

            marker = data[pos + 1]

            # Standalone markers with no length payload
            if marker in (0xD8, 0x00):  # SOI or stuffed byte
                pos += 2
                continue

            if 0xD0 <= marker <= 0xD7:  # RST0 - RST7
                pos += 2
                continue

            if marker == 0xD9:  # EOI found!
                end_pos = pos + 2
                return (end_pos - start, True, metadata)

            if marker == 0xE0:  # APP0 (JFIF)
                metadata["jfif"] = True
            elif marker == 0xE1:  # APP1 (EXIF)
                metadata["exif"] = True

            # Start of Frame markers containing width and height
            if marker in (0xC0, 0xC1, 0xC2):
                if pos + 9 <= limit:
                    # [pos+2:pos+4] length, [pos+4] precision, [pos+5:pos+7] height, [pos+7:pos+9] width
                    h, w = struct.unpack(">HH", data[pos + 5:pos + 9])
                    metadata["height"] = h
                    metadata["width"] = w

            # Start of Scan: entropy-coded scan data follows
            if marker == 0xDA:
                if pos + 4 > limit:
                    break
                sos_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
                pos += 2 + sos_len

                # Scan through entropy data until EOI, next marker, or unallocated block
                while pos < limit - 1:
                    # Check for 512 consecutive zero bytes indicating empty sectors / unallocated space
                    if pos + 512 <= limit and data[pos:pos + 512] == b'\x00' * 512:
                        return (pos - start, False, metadata)

                    # Check for subsequent file headers
                    if data[pos:pos + 2] == b'\xff\xd8':
                        return (pos - start, False, metadata)
                    if pos + 8 <= limit and data[pos:pos + 8] == b'\x89PNG\r\n\x1a\n':
                        return (pos - start, False, metadata)
                    if pos + 4 <= limit and data[pos:pos + 4] in (b'II*\x00', b'MM\x00*'):
                        return (pos - start, False, metadata)
                    if pos + 8 <= limit and data[pos + 4:pos + 8] == b'ftyp':
                        return (pos - start, False, metadata)

                    if data[pos] == 0xFF:
                        next_b = data[pos + 1]
                        if next_b == 0xD9:  # EOI!
                            end_pos = pos + 2
                            return (end_pos - start, True, metadata)
                        elif next_b == 0x00 or (0xD0 <= next_b <= 0xD7):
                            # Stuffed byte or RST marker
                            pos += 2
                        elif next_b in cls.VALID_POST_SOI_MARKERS:
                            # Re-sync on marker
                            break
                        else:
                            pos += 1
                    else:
                        pos += 1
                continue

            # Standard marker with 2-byte length field
            if pos + 4 > limit:
                break

            seg_len = struct.unpack(">H", data[pos + 2:pos + 4])[0]
            if seg_len < 2:
                # Corrupted marker segment length
                pos += 2
                continue
            pos += 2 + seg_len

        # If we reached here without finding EOI, we have a partial / truncated JPEG
        carved_len = min(pos - start, limit - start)
        return (carved_len if carved_len > 1024 else None, False, metadata)


class PNGParser:
    """PNG file carver (Signature: 89 50 4E 47 0D 0A 1A 0A)."""

    SIGNATURE = b'\x89PNG\r\n\x1a\n'
    IHDR = b'IHDR'
    IEND = b'IEND'

    @classmethod
    def is_valid_header(cls, data: bytes, offset: int = 0) -> bool:
        return data[offset:offset + 8] == cls.SIGNATURE

    @classmethod
    def parse_stream(cls, data: bytes, start: int, max_size: int = 100 * 1024 * 1024) -> Tuple[Optional[int], bool, Dict[str, Any]]:
        limit = min(start + max_size, len(data))
        pos = start + 8
        metadata: Dict[str, Any] = {"width": None, "height": None}

        while pos + 8 <= limit:
            chunk_len = struct.unpack(">I", data[pos:pos + 4])[0]
            chunk_type = data[pos + 4:pos + 8]

            if chunk_type == cls.IHDR and pos + 16 <= limit:
                w, h = struct.unpack(">II", data[pos + 8:pos + 16])
                metadata["width"] = w
                metadata["height"] = h

            chunk_total_len = 4 + 4 + chunk_len + 4  # length + type + data + crc
            if chunk_type == cls.IEND:
                end_pos = pos + chunk_total_len
                if end_pos <= len(data):
                    return (end_pos - start, True, metadata)
                return (len(data) - start, False, metadata)

            pos += chunk_total_len

        # Reached limit without IEND
        return (None, False, metadata)


class TIFFRAWParser:
    """TIFF and Camera RAW file carver (Canon CR2, Nikon NEF, Sony ARW, DNG, TIFF)."""

    TIFF_LE = b'II*\x00'  # 49 49 2A 00
    TIFF_BE = b'MM\x00*'  # 4D 4D 00 2A
    CR2_SIG = b'CR\x02\x00'

    @classmethod
    def is_valid_header(cls, data: bytes, offset: int = 0) -> bool:
        if len(data) - offset < 8:
            return False
        header = data[offset:offset + 4]
        return header in (cls.TIFF_LE, cls.TIFF_BE)

    @classmethod
    def parse_stream(cls, data: bytes, start: int, max_size: int = 100 * 1024 * 1024) -> Tuple[Optional[int], bool, Dict[str, Any]]:
        limit = min(start + max_size, len(data))
        if limit - start < 8:
            return (None, False, {})

        is_le = data[start:start + 2] == b'II'
        endian = "<" if is_le else ">"
        ext = "tif"

        # Check for Canon CR2 signature at offset + 8
        if limit - start >= 12 and data[start + 8:start + 12] == cls.CR2_SIG:
            ext = "cr2"

        ifd_offset = struct.unpack(f"{endian}I", data[start + 4:start + 8])[0]
        if ifd_offset < 8 or start + ifd_offset + 2 > limit:
            return (None, False, {})

        # Walk IFD to find largest data pointer
        pos = start + ifd_offset
        num_entries = struct.unpack(f"{endian}H", data[pos:pos + 2])[0]
        pos += 2

        max_offset = ifd_offset + 2 + num_entries * 12 + 4
        metadata: Dict[str, Any] = {"raw_type": ext}

        for _ in range(min(num_entries, 200)):
            if pos + 12 > limit:
                break
            tag, tag_type, count, val_offset = struct.unpack(f"{endian}HHI I", data[pos:pos + 12])
            pos += 12

            # StripOffsets (0x0111) or TileOffsets (0x0144)
            if tag in (0x0111, 0x0144, 0x0117, 0x0145):  # offsets and byte counts
                if val_offset < max_size:
                    max_offset = max(max_offset, val_offset)

            # ImageWidth (0x0100), ImageLength (0x0101)
            if tag == 0x0100:
                metadata["width"] = val_offset
            elif tag == 0x0101:
                metadata["height"] = val_offset

        # Estimate size safely
        estimated_size = min(max_offset + 64 * 1024, limit - start)
        return (estimated_size if estimated_size > 2048 else None, True, metadata)


class HEICParser:
    """
    Carver for High Efficiency Image Format (HEIC/HEIF) photographs.
    Compatible with iPhone (iOS 11+), Android, and modern digital cameras.
    Signatures: ftyp with major brand or compatible brands:
    heic, heix, heim, heis, mif1, msf1, hevc
    """
    FTYP = b'ftyp'
    HEIC_BRANDS = {
        b'heic', b'heix', b'heim', b'heis', b'mif1', b'msf1', b'hevc'
    }

    @classmethod
    def is_valid_header(cls, data: bytes, offset: int = 0) -> bool:
        if len(data) - offset < 16:
            return False
        if data[offset + 4:offset + 8] != cls.FTYP:
            return False
        major_brand = data[offset + 8:offset + 12]
        if major_brand in cls.HEIC_BRANDS:
            return True
        # Check compatible brands in the rest of ftyp box
        ftyp_len = struct.unpack(">I", data[offset:offset + 4])[0]
        if 16 <= ftyp_len <= 128 and len(data) - offset >= ftyp_len:
            compat_data = data[offset + 16:offset + ftyp_len]
            for i in range(0, len(compat_data), 4):
                if compat_data[i:i + 4] in cls.HEIC_BRANDS:
                    return True
        return False

    @classmethod
    def parse_stream(cls, data: bytes, start: int, max_size: int = 100 * 1024 * 1024) -> Tuple[Optional[int], bool, Dict[str, Any]]:
        limit = min(start + max_size, len(data))
        pos = start
        has_meta = False
        has_mdat = False

        while pos + 8 <= limit:
            box_len = struct.unpack(">I", data[pos:pos + 4])[0]
            box_type = data[pos + 4:pos + 8]

            if box_len == 1:
                if pos + 16 > limit:
                    break
                box_len = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            elif box_len == 0:
                box_len = limit - pos

            if box_len < 8:
                break

            if box_type == b'meta':
                has_meta = True
            elif box_type == b'mdat':
                has_mdat = True

            pos += box_len

            if has_meta and has_mdat:
                return (pos - start, True, {"photo_type": "heic"})

        total = pos - start
        if total > 8192 and (has_meta or has_mdat):
            return (total, False, {"photo_type": "heic", "partial": True})
        return (None, False, {})


class WebPParser:
    """WebP image container carver (Signature: RIFF....WEBP)."""

    @classmethod
    def is_valid_header(cls, data: bytes, offset: int = 0) -> bool:
        if len(data) - offset < 12:
            return False
        return data[offset:offset + 4] == b'RIFF' and data[offset + 8:offset + 12] == b'WEBP'

    @classmethod
    def parse_stream(cls, data: bytes, start: int, max_size: int = 50 * 1024 * 1024) -> Tuple[Optional[int], bool, Dict[str, Any]]:
        limit = min(start + max_size, len(data))
        if limit - start < 12:
            return (None, False, {})
        riff_len = struct.unpack("<I", data[start + 4:start + 8])[0]
        total_len = riff_len + 8
        if total_len > max_size or total_len < 16:
            return (None, False, {})
        if start + total_len <= len(data):
            return (total_len, True, {"photo_type": "webp"})
        return (len(data) - start, False, {"photo_type": "webp", "partial": True})


class MP4VideoParser:
    """MP4 and QuickTime MOV video container carver."""

    FTYP = b'ftyp'
    VALID_BRANDS = {
        b'isom', b'iso2', b'mp41', b'mp42', b'qt  ', b'M4A ',
        b'M4V ', b'avc1', b'MSNV'
    }

    @classmethod
    def is_valid_header(cls, data: bytes, offset: int = 0) -> bool:
        if len(data) - offset < 16:
            return False
        # ftyp box starts at offset + 4
        if data[offset + 4:offset + 8] != cls.FTYP:
            return False
        brand = data[offset + 8:offset + 12]
        return brand in cls.VALID_BRANDS or (brand.isalnum() and brand not in HEICParser.HEIC_BRANDS)

    @classmethod
    def parse_stream(cls, data: bytes, start: int, max_size: int = 500 * 1024 * 1024) -> Tuple[Optional[int], bool, Dict[str, Any]]:
        limit = min(start + max_size, len(data))
        pos = start
        has_moov = False
        has_mdat = False

        while pos + 8 <= limit:
            box_len = struct.unpack(">I", data[pos:pos + 4])[0]
            box_type = data[pos + 4:pos + 8]

            if box_len == 1:
                # 64-bit extended size
                if pos + 16 > limit:
                    break
                box_len = struct.unpack(">Q", data[pos + 8:pos + 16])[0]
            elif box_len == 0:
                # Extends to end of file
                box_len = limit - pos

            if box_len < 8:
                break

            if box_type == b'moov':
                has_moov = True
            elif box_type == b'mdat':
                has_mdat = True

            pos += box_len

            # If we found both moov and mdat, we have a complete video structure!
            if has_moov and has_mdat:
                return (pos - start, True, {"video": True})

        total = pos - start
        if total > 64 * 1024 and (has_moov or has_mdat):
            return (total, False, {"video": True, "partial": True})
        return (None, False, {})


class MultiFormatCarver:
    """Unified multi-format file recognizer and carver."""

    @staticmethod
    def identify_at_offset(data: bytes, offset: int = 0) -> Tuple[MediaType, Optional[str]]:
        """Identifies file type candidate at given byte offset."""
        if JPEGParser.is_valid_header(data, offset):
            return MediaType.JPEG, "jpg"
        if PNGParser.is_valid_header(data, offset):
            return MediaType.PNG, "png"
        if HEICParser.is_valid_header(data, offset):
            return MediaType.HEIC, "heic"
        if WebPParser.is_valid_header(data, offset):
            return MediaType.WEBP, "webp"
        if TIFFRAWParser.is_valid_header(data, offset):
            ext = "cr2" if (len(data) - offset >= 12 and data[offset + 8:offset + 12] == TIFFRAWParser.CR2_SIG) else "tif"
            return MediaType.TIFF_RAW, ext
        if MP4VideoParser.is_valid_header(data, offset):
            return MediaType.MP4_VIDEO, "mp4"
        return MediaType.UNKNOWN, None
