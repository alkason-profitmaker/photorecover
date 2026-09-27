"""
JPEG Repair and Truncation Recovery Module
Repairs damaged, truncated, or partially overwritten photos to make them viewable.
"""

from io import BytesIO
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageFile
import struct

# Allow Pillow to load truncated images during repair inspection
ImageFile.LOAD_TRUNCATED_IMAGES = True


class JPEGRepairer:
    """Repairs truncated and damaged JPEG images."""

    EOI = b'\xff\xd9'

    # Standard default baseline luminance and chrominance Huffman tables
    # Used when a camera image fragment has lost its DHT segment
    STANDARD_DHT = (
        b'\xff\xc4\x01\xa2'
        b'\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b'
        b'\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d'
        b'\x01\x02\x03\x00\x04\x11\x05\x12\x21\x31\x41\x06\x13\x51\x61\x07'
        b'\x22\x71\x14\x32\x81\x91\xa1\x08\x23\x42\xb1\xc1\x15\x52\xd1\xf0'
        b'\x24\x33\x62\x72\x82\x09\x0a\x16\x17\x18\x19\x1a\x25\x26\x27\x28'
        b'\x29\x2a\x34\x35\x36\x37\x38\x39\x3a\x43\x44\x45\x46\x47\x48\x49'
        b'\x4a\x53\x54\x55\x56\x57\x58\x59\x5a\x63\x64\x65\x66\x67\x68\x69'
        b'\x6a\x73\x74\x75\x76\x77\x78\x79\x7a\x83\x84\x85\x86\x87\x88\x89'
        b'\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7'
        b'\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5'
        b'\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2'
        b'\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8'
        b'\xf9\xfa'
        b'\x01\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00'
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b'
        b'\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02\x77'
        b'\x00\x01\x02\x03\x11\x04\x05\x21\x31\x06\x12\x41\x51\x07\x61\x71'
        b'\x13\x22\x32\x81\x08\x14\x42\x91\xa1\xb1\xc1\x09\x23\x33\x52\xf0'
        b'\x15\x62\x72\xd1\x0a\x16\x24\x34\xe1\x25\xf1\x17\x18\x19\x1a\x26'
        b'\x27\x28\x29\x2a\x35\x36\x37\x38\x39\x3a\x43\x44\x45\x46\x47\x48'
        b'\x49\x4a\x53\x54\x55\x56\x57\x58\x59\x5a\x63\x64\x65\x66\x67\x68'
        b'\x69\x6a\x73\x74\x75\x76\x77\x78\x79\x7a\x82\x83\x84\x85\x86\x87'
        b'\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5'
        b'\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3'
        b'\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda'
        b'\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8'
        b'\xf9\xfa'
    )

    @classmethod
    def attempt_repair(cls, data: bytes) -> Tuple[Optional[bytes], bool, Dict[str, Any]]:
        """
        Attempts to repair truncated or damaged JPEG data.
        Returns: (repaired_data, was_repaired, metadata_dict)
        """
        if len(data) < 128:
            return (None, False, {"error": "Buffer too small"})

        # Must start with SOI
        if data[:2] != b'\xff\xd8':
            # Check if SOI is within first 16 bytes
            soi_idx = data.find(b'\xff\xd8')
            if soi_idx != -1 and soi_idx < 16:
                data = data[soi_idx:]
            else:
                return (None, False, {"error": "No SOI marker"})

        # Case 1: Already has EOI at the end
        if data.endswith(cls.EOI):
            valid, w, h = cls._test_decode(data)
            if valid:
                return (data, False, {"width": w, "height": h, "repaired": False})

        repaired_buf = bytearray(data)

        # Case 2: Truncated missing EOI
        if not repaired_buf.endswith(cls.EOI):
            # Check if DHT is missing before SOS
            has_dht = b'\xff\xc4' in repaired_buf
            sos_pos = repaired_buf.find(b'\xff\xda')

            if not has_dht and sos_pos != -1:
                # Inject standard DHT tables before SOS
                repaired_buf = repaired_buf[:sos_pos] + bytearray(cls.STANDARD_DHT) + repaired_buf[sos_pos:]

            # Append clean EOI marker
            repaired_buf.extend(cls.EOI)

            # Test decode
            valid, w, h = cls._test_decode(bytes(repaired_buf))
            if valid:
                return (bytes(repaired_buf), True, {
                    "width": w,
                    "height": h,
                    "repaired": True,
                    "technique": "EOI_and_table_repair"
                })

        # Case 3: Scan data corrupted at end
        # Try trimming back in 1KB increments to find last decodeable raster block
        for trim in (1024, 4096, 16384):
            if len(data) > trim + 512:
                candidate = bytearray(data[:-trim])
                candidate.extend(cls.EOI)
                valid, w, h = cls._test_decode(bytes(candidate))
                if valid:
                    return (bytes(candidate), True, {
                        "width": w,
                        "height": h,
                        "repaired": True,
                        "technique": f"tail_trim_{trim}"
                    })

        return (None, False, {"error": "Unable to decode after repair attempts"})

    @staticmethod
    def _test_decode(data: bytes) -> Tuple[bool, Optional[int], Optional[int]]:
        """Validates if bytes can be rendered by PIL."""
        try:
            with Image.open(BytesIO(data)) as img:
                img.verify()

            # Re-open to read dimensions and load pixel bitmap
            with Image.open(BytesIO(data)) as img:
                w, h = img.size
                # Try loading at least the first band
                img.load()
                if w >= 10 and h >= 10:
                    return True, w, h
        except Exception:
            pass
        return False, None, None
