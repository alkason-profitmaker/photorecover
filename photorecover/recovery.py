"""
SD Card Image Recovery Module

Properly recovers JPEG images from formatted/corrupted SD cards by:
1. Scanning for JPEG file signatures (headers and footers)
2. Validating image structure and integrity
3. Deduplicating using content hashing
4. Recovering complete images only
"""

import os
import hashlib
import struct
from pathlib import Path
from typing import Optional, List, Tuple, Set, Generator, BinaryIO
from dataclasses import dataclass
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import threading

# Try to import PIL for image validation
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class RecoveredImage:
    """Represents a recovered image with metadata."""
    data: bytes
    offset: int  # Byte offset in source
    size: int
    hash: str
    is_valid: bool
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None


class JPEGSignatures:
    """JPEG file format signatures and markers."""

    # JPEG Start of Image marker
    SOI = b'\xff\xd8'

    # JPEG End of Image marker
    EOI = b'\xff\xd9'

    # Common JPEG APP markers (appear after SOI)
    APP0_JFIF = b'\xff\xd8\xff\xe0'  # JFIF
    APP1_EXIF = b'\xff\xd8\xff\xe1'  # EXIF (most camera photos)
    APP2 = b'\xff\xd8\xff\xe2'       # ICC Profile

    # Start of Frame markers (indicate image dimensions)
    SOF0 = b'\xff\xc0'  # Baseline DCT
    SOF1 = b'\xff\xc1'  # Extended sequential DCT
    SOF2 = b'\xff\xc2'  # Progressive DCT

    # Other important markers
    DQT = b'\xff\xdb'   # Define Quantization Table
    DHT = b'\xff\xc4'   # Define Huffman Table
    SOS = b'\xff\xda'   # Start of Scan (image data follows)

    # Maximum reasonable JPEG size (50MB - adjust if needed)
    MAX_JPEG_SIZE = 50 * 1024 * 1024

    # Minimum reasonable JPEG size (1KB)
    MIN_JPEG_SIZE = 1024


class SDCardRecovery:
    """
    SD Card image recovery class for extracting JPEG images from
    formatted or corrupted storage devices.
    """

    def __init__(self,
                 validate_images: bool = True,
                 deduplicate: bool = True,
                 min_size: int = JPEGSignatures.MIN_JPEG_SIZE,
                 max_size: int = JPEGSignatures.MAX_JPEG_SIZE,
                 verbose: bool = True):
        """
        Initialize the recovery module.

        Args:
            validate_images: Whether to validate recovered images using PIL
            deduplicate: Whether to skip duplicate images based on hash
            min_size: Minimum valid JPEG size in bytes
            max_size: Maximum valid JPEG size in bytes
            verbose: Print progress information
        """
        self.validate_images = validate_images and PIL_AVAILABLE
        self.deduplicate = deduplicate
        self.min_size = min_size
        self.max_size = max_size
        self.verbose = verbose

        self._seen_hashes: Set[str] = set()
        self._lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_found': 0,
            'valid_images': 0,
            'duplicates_skipped': 0,
            'invalid_skipped': 0,
            'too_small': 0,
            'too_large': 0,
            'incomplete': 0
        }

    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _calculate_hash(self, data: bytes) -> str:
        """Calculate SHA-256 hash of image data."""
        return hashlib.sha256(data).hexdigest()[:16]

    def _is_duplicate(self, hash_value: str) -> bool:
        """Check if we've already seen this image."""
        if not self.deduplicate:
            return False

        with self._lock:
            if hash_value in self._seen_hashes:
                return True
            self._seen_hashes.add(hash_value)
            return False

    def _validate_jpeg(self, data: bytes) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
        """
        Validate JPEG data and extract dimensions.

        Returns:
            Tuple of (is_valid, width, height, error_message)
        """
        if not PIL_AVAILABLE:
            # Basic validation without PIL
            if data[:2] != JPEGSignatures.SOI:
                return False, None, None, "Missing SOI marker"
            if data[-2:] != JPEGSignatures.EOI:
                return False, None, None, "Missing EOI marker"
            return True, None, None, None

        try:
            img = Image.open(BytesIO(data))
            img.verify()  # Verify it's a valid image

            # Re-open to get dimensions (verify() closes the image)
            img = Image.open(BytesIO(data))
            width, height = img.size

            # Check for reasonable dimensions
            if width < 10 or height < 10:
                return False, width, height, "Image too small"
            if width > 20000 or height > 20000:
                return False, width, height, "Image dimensions unreasonable"

            return True, width, height, None

        except Exception as e:
            return False, None, None, str(e)

    def _find_jpeg_end(self, data: bytes, start: int) -> Optional[int]:
        """
        Find the end of a JPEG image starting at the given offset.

        This properly handles embedded thumbnails and JPEG structure
        to find the actual end of the image.

        Args:
            data: Raw data to search
            start: Starting offset (should be at SOI marker)

        Returns:
            Offset of the byte after EOI marker, or None if not found
        """
        pos = start + 2  # Skip SOI marker
        data_len = len(data)
        max_end = min(start + self.max_size, data_len)

        while pos < max_end - 1:
            # Look for marker prefix
            if data[pos] != 0xFF:
                pos += 1
                continue

            marker = data[pos:pos + 2]

            # End of Image marker - we found it!
            if marker == JPEGSignatures.EOI:
                return pos + 2

            # Skip padding bytes (0xFF followed by 0xFF or 0x00)
            if data[pos + 1] == 0xFF or data[pos + 1] == 0x00:
                pos += 1
                continue

            # Start of Scan - image data follows, search for EOI differently
            if marker == JPEGSignatures.SOS:
                # Skip SOS header
                if pos + 4 > max_end:
                    return None
                sos_len = struct.unpack('>H', data[pos + 2:pos + 4])[0]
                pos += 2 + sos_len

                # Now scan through entropy-coded data looking for EOI
                while pos < max_end - 1:
                    if data[pos] == 0xFF and data[pos + 1] == 0xD9:
                        return pos + 2
                    elif data[pos] == 0xFF and data[pos + 1] == 0x00:
                        # Stuffed byte, skip
                        pos += 2
                    elif data[pos] == 0xFF and 0xD0 <= data[pos + 1] <= 0xD7:
                        # RST marker, skip
                        pos += 2
                    else:
                        pos += 1
                return None

            # Regular marker with length field
            if pos + 4 > max_end:
                return None

            try:
                segment_len = struct.unpack('>H', data[pos + 2:pos + 4])[0]
                pos += 2 + segment_len
            except:
                pos += 1

        return None

    def _find_all_jpeg_starts(self, data: bytes) -> Generator[int, None, None]:
        """
        Find all potential JPEG start positions in the data.

        Yields:
            Byte offsets where JPEG SOI markers are found
        """
        pos = 0
        data_len = len(data)

        while pos < data_len - 1:
            # Find next SOI marker
            idx = data.find(JPEGSignatures.SOI, pos)
            if idx == -1:
                break

            # Verify it looks like a real JPEG (check for APP marker)
            if idx + 4 <= data_len:
                next_bytes = data[idx + 2:idx + 4]
                # Check for common APP markers or other valid markers
                if next_bytes[0:1] == b'\xff' and next_bytes[1:2] in (
                    b'\xe0', b'\xe1', b'\xe2', b'\xe3',  # APP0-3
                    b'\xdb', b'\xc0', b'\xc2', b'\xc4'   # DQT, SOF0, SOF2, DHT
                ):
                    yield idx

            pos = idx + 1

    def recover_from_file(self,
                          source_path: str,
                          output_dir: str,
                          block_size: int = 64 * 1024 * 1024,
                          progress_callback=None) -> List[str]:
        """
        Recover JPEG images from a file or device.

        Args:
            source_path: Path to SD card device (e.g., /dev/sdb) or image file
            output_dir: Directory to save recovered images
            block_size: Size of blocks to read at a time (default 64MB)
            progress_callback: Optional callback(bytes_processed, total_bytes)

        Returns:
            List of paths to recovered image files
        """
        source_path = Path(source_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        recovered_files = []

        # Get total size
        if source_path.is_block_device() if hasattr(source_path, 'is_block_device') else False:
            # For block devices, try to get size
            try:
                with open(source_path, 'rb') as f:
                    f.seek(0, 2)
                    total_size = f.tell()
            except:
                total_size = 0
        else:
            total_size = source_path.stat().st_size

        self._log(f"Scanning {source_path} ({total_size / (1024*1024):.1f} MB)")
        self._log(f"Output directory: {output_dir}")

        # Reset statistics
        self.stats = {k: 0 for k in self.stats}
        self._seen_hashes.clear()

        bytes_processed = 0
        image_count = 0
        overlap = self.max_size  # Overlap to catch images spanning blocks

        with open(source_path, 'rb') as f:
            prev_tail = b''

            while True:
                # Read block with overlap from previous
                block = prev_tail + f.read(block_size)
                if len(block) <= len(prev_tail):
                    break  # End of file

                # Find all JPEG images in this block
                for jpeg_start in self._find_all_jpeg_starts(block):
                    # Skip if we already processed this in previous block
                    if jpeg_start < len(prev_tail) - 2:
                        continue

                    # Find the end of this JPEG
                    jpeg_end = self._find_jpeg_end(block, jpeg_start)

                    if jpeg_end is None:
                        self.stats['incomplete'] += 1
                        continue

                    jpeg_data = block[jpeg_start:jpeg_end]
                    jpeg_size = len(jpeg_data)

                    self.stats['total_found'] += 1

                    # Size checks
                    if jpeg_size < self.min_size:
                        self.stats['too_small'] += 1
                        continue
                    if jpeg_size > self.max_size:
                        self.stats['too_large'] += 1
                        continue

                    # Calculate hash for deduplication
                    img_hash = self._calculate_hash(jpeg_data)

                    if self._is_duplicate(img_hash):
                        self.stats['duplicates_skipped'] += 1
                        continue

                    # Validate image
                    is_valid, width, height, error = self._validate_jpeg(jpeg_data)

                    if not is_valid:
                        self.stats['invalid_skipped'] += 1
                        continue

                    # Save the image
                    image_count += 1

                    # Create filename with dimensions if available
                    if width and height:
                        filename = f"recovered_{image_count:05d}_{width}x{height}.jpg"
                    else:
                        filename = f"recovered_{image_count:05d}.jpg"

                    output_path = output_dir / filename

                    with open(output_path, 'wb') as out_f:
                        out_f.write(jpeg_data)

                    recovered_files.append(str(output_path))
                    self.stats['valid_images'] += 1

                    if self.verbose and self.stats['valid_images'] % 10 == 0:
                        self._log(f"  Recovered {self.stats['valid_images']} images...")

                # Keep tail for overlap
                prev_tail = block[-overlap:] if len(block) > overlap else block
                bytes_processed += block_size

                if progress_callback:
                    progress_callback(bytes_processed, total_size)

        self._print_summary()
        return recovered_files

    def recover_from_bytes(self, data: bytes, output_dir: str) -> List[str]:
        """
        Recover JPEG images from raw bytes.

        Args:
            data: Raw bytes to scan
            output_dir: Directory to save recovered images

        Returns:
            List of paths to recovered image files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        recovered_files = []
        self.stats = {k: 0 for k in self.stats}
        self._seen_hashes.clear()

        image_count = 0

        for jpeg_start in self._find_all_jpeg_starts(data):
            jpeg_end = self._find_jpeg_end(data, jpeg_start)

            if jpeg_end is None:
                self.stats['incomplete'] += 1
                continue

            jpeg_data = data[jpeg_start:jpeg_end]
            jpeg_size = len(jpeg_data)

            self.stats['total_found'] += 1

            if jpeg_size < self.min_size:
                self.stats['too_small'] += 1
                continue
            if jpeg_size > self.max_size:
                self.stats['too_large'] += 1
                continue

            img_hash = self._calculate_hash(jpeg_data)

            if self._is_duplicate(img_hash):
                self.stats['duplicates_skipped'] += 1
                continue

            is_valid, width, height, error = self._validate_jpeg(jpeg_data)

            if not is_valid:
                self.stats['invalid_skipped'] += 1
                continue

            image_count += 1

            if width and height:
                filename = f"recovered_{image_count:05d}_{width}x{height}.jpg"
            else:
                filename = f"recovered_{image_count:05d}.jpg"

            output_path = output_dir / filename

            with open(output_path, 'wb') as out_f:
                out_f.write(jpeg_data)

            recovered_files.append(str(output_path))
            self.stats['valid_images'] += 1

        self._print_summary()
        return recovered_files

    def _print_summary(self):
        """Print recovery summary statistics."""
        if not self.verbose:
            return

        self._log("\n" + "=" * 50)
        self._log("Recovery Summary")
        self._log("=" * 50)
        self._log(f"Total JPEG signatures found: {self.stats['total_found']}")
        self._log(f"Valid images recovered: {self.stats['valid_images']}")
        self._log(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        self._log(f"Invalid/corrupted skipped: {self.stats['invalid_skipped']}")
        self._log(f"Too small (< {self.min_size} bytes): {self.stats['too_small']}")
        self._log(f"Incomplete (no EOI found): {self.stats['incomplete']}")
        self._log("=" * 50)


def recover_images(source: str,
                   output_dir: str,
                   validate: bool = True,
                   deduplicate: bool = True,
                   min_size: int = 1024,
                   max_size: int = 50 * 1024 * 1024,
                   verbose: bool = True) -> List[str]:
    """
    Convenience function to recover JPEG images from a source.

    Args:
        source: Path to SD card device or image file
        output_dir: Directory to save recovered images
        validate: Validate recovered images
        deduplicate: Skip duplicate images
        min_size: Minimum JPEG size in bytes
        max_size: Maximum JPEG size in bytes
        verbose: Print progress information

    Returns:
        List of paths to recovered image files
    """
    recovery = SDCardRecovery(
        validate_images=validate,
        deduplicate=deduplicate,
        min_size=min_size,
        max_size=max_size,
        verbose=verbose
    )

    return recovery.recover_from_file(source, output_dir)
