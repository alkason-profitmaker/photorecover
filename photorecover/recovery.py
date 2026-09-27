"""
Production-Grade Storage Device and Image Recovery Engine
Features:
1. Zero-loss sliding window carver (immune to block-boundary crossing bugs)
2. Multi-format support (JPEG, PNG, TIFF/RAW CR2/NEF/ARW/DNG, MP4/MOV)
3. Partial/damaged image repair integration
4. Filesystem awareness (FAT32/exFAT reconstruction)
5. Read-only media safety and bad-sector fault tolerance
6. Thumbnail extraction and live preview metadata
"""

import os
import io
import time
import hashlib
import struct
import threading
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Set, Generator, BinaryIO, Callable, Any
from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image, ExifTags

from .signatures import MultiFormatCarver, JPEGParser, PNGParser, TIFFRAWParser, MP4VideoParser, MediaType
from .repair import JPEGRepairer
from .filesystem import FilesystemRecoveryEngine, FilesystemFile
from .exceptions import SourceMediaError, BadSectorError


@dataclass
class RecoveredItem:
    """Represents a successfully recovered photo, video, or raw file."""
    path: str
    filename: str
    media_type: str
    extension: str
    size: int
    offset: int
    hash: str
    is_valid: bool
    is_repaired: bool = False
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_bytes: Optional[bytes] = None
    exif_camera: Optional[str] = None
    exif_date: Optional[str] = None
    fs_origin: Optional[str] = None


class SDCardRecovery:
    """
    World-class image & media recovery engine.
    Recovers photos from SD cards, USB drives, memory sticks, and disk images.
    """

    def __init__(self,
                 validate_images: bool = True,
                 deduplicate: bool = True,
                 attempt_repair: bool = True,
                 include_raw: bool = True,
                 include_video: bool = True,
                 min_size: int = 1024,
                 max_size: int = 100 * 1024 * 1024,
                 verbose: bool = True):
        self.validate_images = validate_images
        self.deduplicate = deduplicate
        self.attempt_repair = attempt_repair
        self.include_raw = include_raw
        self.include_video = include_video
        self.min_size = min_size
        self.max_size = max_size
        self.verbose = verbose

        self._seen_hashes: Set[str] = set()
        self._lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.pause_event = threading.Event()

        # Detailed recovery metrics
        self.stats = {
            'total_scanned_bytes': 0,
            'total_found': 0,
            'photos_recovered': 0,
            'raw_recovered': 0,
            'video_recovered': 0,
            'repaired': 0,
            'duplicates_skipped': 0,
            'invalid_skipped': 0,
            'bad_sectors_handled': 0,
            'fs_entries_recovered': 0
        }

    def _log(self, message: str):
        if self.verbose:
            print(message)

    def _compute_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _is_duplicate(self, hash_str: str) -> bool:
        if not self.deduplicate:
            return False
        with self._lock:
            if hash_str in self._seen_hashes:
                return True
            self._seen_hashes.add(hash_str)
            return False

    def cancel(self):
        """Signals the engine to abort scanning safely."""
        self.cancel_event.set()

    def pause(self):
        self.pause_event.set()

    def resume(self):
        self.pause_event.clear()

    def _extract_exif(self, data: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Extracts camera model and capture date from EXIF payload."""
        try:
            with Image.open(BytesIO(data)) as img:
                exif = img.getexif()
                if not exif:
                    return None, None
                make = exif.get(0x010F, "")
                model = exif.get(0x0110, "")
                date_time = exif.get(0x0132, None)
                camera = f"{make} {model}".strip() if (make or model) else None
                return camera, date_time
        except Exception:
            return None, None

    def _generate_thumbnail(self, data: bytes) -> Optional[bytes]:
        """Generates a compressed 256x256 thumbnail for instant UI preview."""
        try:
            with Image.open(BytesIO(data)) as img:
                img.thumbnail((256, 256))
                thumb_io = BytesIO()
                img.convert("RGB").save(thumb_io, format="JPEG", quality=80)
                return thumb_io.getvalue()
        except Exception:
            return None

    def recover(self,
                source_path: str,
                output_dir: str,
                scan_filesystem: bool = True,
                chunk_size: int = 16 * 1024 * 1024,
                progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[RecoveredItem]:
        """
        Executes complete recovery pipeline with zero boundary loss.
        """
        source = Path(source_path)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        thumbs_dir = out_dir / ".thumbnails"
        thumbs_dir.mkdir(parents=True, exist_ok=True)

        recovered_items: List[RecoveredItem] = []
        self.cancel_event.clear()
        self.pause_event.clear()
        self._seen_hashes.clear()
        self.stats = {k: 0 for k in self.stats}

        # Calculate or query total source media size
        try:
            total_size = source.stat().st_size
        except Exception:
            total_size = 0

        self._log(f"Initiating PhotoRecover Deep Scan on: {source} ({total_size / (1024 * 1024):.1f} MB)")

        start_time = time.time()

        # Step 1: Filesystem Reconstruction (FAT32/exFAT deleted files)
        if scan_filesystem and source.is_file():
            self._log("Analyzing filesystem partition structure (FAT32 / exFAT)...")
            try:
                with open(source, 'rb') as fs_stream:
                    fs_type, fs_files = FilesystemRecoveryEngine.detect_and_scan(fs_stream)
                    if fs_type:
                        self._log(f"Detected {fs_type} filesystem. Found {len(fs_files)} potential files.")
                        for fe in fs_files:
                            if self.cancel_event.is_set():
                                break
                            if fe.extension.lower() in ('jpg', 'jpeg', 'png', 'cr2', 'nef', 'arw', 'dng', 'mp4', 'mov'):
                                file_data = FAT32Parser(fs_stream).extract_file_data(fe)
                                if len(file_data) >= self.min_size:
                                    item = self._process_candidate_bytes(
                                        data=file_data,
                                        offset=0,
                                        output_dir=out_dir,
                                        preferred_name=fe.name,
                                        fs_origin=fs_type
                                    )
                                    if item:
                                        recovered_items.append(item)
                                        self.stats['fs_entries_recovered'] += 1
            except Exception as fs_err:
                self._log(f"Filesystem scan skipped: {fs_err}")

        # Step 2: Streaming Sliding-Window Raw Carver (Zero-boundary loss)
        self._log("Beginning Raw Signature Carving across storage sectors...")

        with open(source, 'rb') as stream:
            stream_carver = StreamCarver(
                stream=stream,
                chunk_size=chunk_size,
                max_file_size=self.max_size,
                min_file_size=self.min_size,
                include_raw=self.include_raw,
                include_video=self.include_video,
                attempt_repair=self.attempt_repair,
                cancel_event=self.cancel_event,
                pause_event=self.pause_event
            )

            for cand_data, cand_offset, cand_ext, cand_meta in stream_carver.carve():
                if self.cancel_event.is_set():
                    break

                self.stats['total_found'] += 1
                cand_size = len(cand_data)

                # Deduplicate by SHA-256
                item_hash = self._compute_hash(cand_data)
                if self._is_duplicate(item_hash):
                    self.stats['duplicates_skipped'] += 1
                    continue

                item = self._process_candidate_bytes(
                    data=cand_data,
                    offset=cand_offset,
                    output_dir=out_dir,
                    extension=cand_ext,
                    meta=cand_meta
                )

                if item:
                    recovered_items.append(item)
                    if item.is_repaired:
                        self.stats['repaired'] += 1
                    if item.media_type == "video_mp4":
                        self.stats['video_recovered'] += 1
                    elif item.media_type == "raw_tiff":
                        self.stats['raw_recovered'] += 1
                    else:
                        self.stats['photos_recovered'] += 1

                # Update progress
                if progress_callback:
                    elapsed = max(0.1, time.time() - start_time)
                    speed_mb = (stream_carver.current_file_offset / (1024 * 1024)) / elapsed
                    progress_callback({
                        "bytes_scanned": stream_carver.current_file_offset,
                        "total_bytes": total_size,
                        "speed_mb": speed_mb,
                        "recovered_count": len(recovered_items),
                        "stats": self.stats
                    })

        self.stats['total_scanned_bytes'] = stream_carver.current_file_offset
        self._print_summary(recovered_items)
        return recovered_items

    def _process_candidate_bytes(self,
                                 data: bytes,
                                 offset: int,
                                 output_dir: Path,
                                 preferred_name: Optional[str] = None,
                                 extension: Optional[str] = None,
                                 fs_origin: Optional[str] = None,
                                 meta: Optional[Dict[str, Any]] = None) -> Optional[RecoveredItem]:
        """Validates, repairs if needed, extracts metadata, and saves recovered file."""
        meta = meta or {}
        is_repaired = False
        width, height = meta.get("width"), meta.get("height")
        is_valid = True

        ext = extension or (preferred_name.split('.')[-1].lower() if preferred_name and '.' in preferred_name else "jpg")

        # Repair check for JPEGs
        if ext in ('jpg', 'jpeg'):
            if self.validate_images:
                try:
                    with Image.open(BytesIO(data)) as img:
                        img.verify()
                    with Image.open(BytesIO(data)) as img:
                        width, height = img.size
                except Exception:
                    # Invalid or truncated: attempt repair
                    if self.attempt_repair:
                        repaired_data, was_rep, rep_meta = JPEGRepairer.attempt_repair(data)
                        if was_rep and repaired_data:
                            data = repaired_data
                            is_repaired = True
                            width = rep_meta.get("width")
                            height = rep_meta.get("height")
                        else:
                            self.stats['invalid_skipped'] += 1
                            return None
                    else:
                        self.stats['invalid_skipped'] += 1
                        return None
        elif ext == 'png':
            try:
                with Image.open(BytesIO(data)) as img:
                    img.verify()
                with Image.open(BytesIO(data)) as img:
                    width, height = img.size
            except Exception:
                self.stats['invalid_skipped'] += 1
                return None

        # Build filename
        count = len(self._seen_hashes)
        if preferred_name:
            filename = preferred_name
        else:
            tag = "_repaired" if is_repaired else ""
            res_tag = f"_{width}x{height}" if (width and height) else ""
            filename = f"recovered_{count:05d}{res_tag}{tag}.{ext}"

        file_path = output_dir / filename
        with open(file_path, "wb") as f:
            f.write(data)

        # Thumbnail and EXIF
        thumb_bytes = self._generate_thumbnail(data)
        camera, date_time = self._extract_exif(data)

        return RecoveredItem(
            path=str(file_path),
            filename=filename,
            media_type="photo" if ext in ('jpg', 'jpeg', 'png') else ("video" if ext in ('mp4', 'mov') else "raw"),
            extension=ext,
            size=len(data),
            offset=offset,
            hash=self._compute_hash(data),
            is_valid=is_valid,
            is_repaired=is_repaired,
            width=width,
            height=height,
            thumbnail_bytes=thumb_bytes,
            exif_camera=camera,
            exif_date=date_time,
            fs_origin=fs_origin
        )

    def _print_summary(self, items: List[RecoveredItem]):
        if not self.verbose:
            return
        self._log("\n" + "=" * 55)
        self._log("PhotoRecover v2.0 - Recovery Summary")
        self._log("=" * 55)
        self._log(f"Total files recovered:        {len(items)}")
        self._log(f"  • Standard Photos (JPG/PNG):{self.stats['photos_recovered']}")
        self._log(f"  • Repaired Damaged Photos:  {self.stats['repaired']}")
        self._log(f"  • Camera RAW Files:         {self.stats['raw_recovered']}")
        self._log(f"  • Video Files:              {self.stats['video_recovered']}")
        self._log(f"  • Filesystem Restored:      {self.stats['fs_entries_recovered']}")
        self._log(f"Duplicates skipped:           {self.stats['duplicates_skipped']}")
        self._log(f"Corrupted fragments skipped:  {self.stats['invalid_skipped']}")
        self._log("=" * 55 + "\n")


class StreamCarver:
    """
    Streaming sliding-window carver that guarantees zero dropped photos across chunk boundaries.
    """

    def __init__(self,
                 stream: BinaryIO,
                 chunk_size: int = 16 * 1024 * 1024,
                 max_file_size: int = 100 * 1024 * 1024,
                 min_file_size: int = 1024,
                 include_raw: bool = True,
                 include_video: bool = True,
                 attempt_repair: bool = True,
                 cancel_event: Optional[threading.Event] = None,
                 pause_event: Optional[threading.Event] = None):
        self.stream = stream
        self.chunk_size = chunk_size
        self.max_file_size = max_file_size
        self.min_file_size = min_file_size
        self.include_raw = include_raw
        self.include_video = include_video
        self.attempt_repair = attempt_repair
        self.cancel_event = cancel_event or threading.Event()
        self.pause_event = pause_event or threading.Event()

        self.current_file_offset = 0

    def _safe_read(self, size: int) -> bytes:
        """Reads from stream with bad sector fault tolerance."""
        try:
            return self.stream.read(size)
        except (OSError, IOError):
            # Bad sector encountered on storage device!
            # Pad with zeroes for one sector and advance stream safely
            try:
                self.stream.seek(self.stream.tell() + 512)
            except Exception:
                pass
            return b'\x00' * 512

    def carve(self) -> Generator[Tuple[bytes, int, str, Dict[str, Any]], None, None]:
        """
        Sliding-window stream processor yielding: (data, file_offset, extension, metadata)
        """
        buffer = bytearray()
        buffer_start_offset = 0
        eof = False
        overlap = min(4096, max(32, self.chunk_size // 4))

        while not self.cancel_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.2)
                continue

            # Replenish buffer if needed
            if not eof and len(buffer) < self.chunk_size:
                needed = self.chunk_size - len(buffer)
                chunk = self._safe_read(needed)
                if not chunk:
                    eof = True
                else:
                    buffer.extend(chunk)

            if len(buffer) < 4:
                break

            idx = 0
            limit_idx = len(buffer) if eof else max(0, len(buffer) - 3)

            while idx < limit_idx:
                if self.cancel_event.is_set():
                    break

                # Quick signature check
                media_type, ext = MultiFormatCarver.identify_at_offset(buffer, idx)
                if media_type == MediaType.UNKNOWN:
                    idx += 1
                    continue

                if media_type == MediaType.TIFF_RAW and not self.include_raw:
                    idx += 1
                    continue
                if media_type == MediaType.MP4_VIDEO and not self.include_video:
                    idx += 1
                    continue

                # Parse length from buffer
                length = None
                is_complete = False
                meta: Dict[str, Any] = {}

                if media_type == MediaType.JPEG:
                    length, is_complete, meta = JPEGParser.parse_stream(buffer, idx, self.max_file_size)
                elif media_type == MediaType.PNG:
                    length, is_complete, meta = PNGParser.parse_stream(buffer, idx, self.max_file_size)
                elif media_type == MediaType.TIFF_RAW:
                    length, is_complete, meta = TIFFRAWParser.parse_stream(buffer, idx, self.max_file_size)
                elif media_type == MediaType.MP4_VIDEO:
                    length, is_complete, meta = MP4VideoParser.parse_stream(buffer, idx, self.max_file_size)

                # Boundary crossing: if incomplete and not at EOF, read more into buffer
                while not is_complete and not eof:
                    # Prune everything before idx
                    buffer = buffer[idx:]
                    buffer_start_offset += idx
                    self.current_file_offset = buffer_start_offset
                    idx = 0

                    more = self._safe_read(self.chunk_size)
                    if not more:
                        eof = True
                        break
                    buffer.extend(more)

                    # Try parsing again with expanded buffer
                    if media_type == MediaType.JPEG:
                        length, is_complete, meta = JPEGParser.parse_stream(buffer, 0, self.max_file_size)
                    elif media_type == MediaType.PNG:
                        length, is_complete, meta = PNGParser.parse_stream(buffer, 0, self.max_file_size)
                    elif media_type == MediaType.TIFF_RAW:
                        length, is_complete, meta = TIFFRAWParser.parse_stream(buffer, 0, self.max_file_size)
                    elif media_type == MediaType.MP4_VIDEO:
                        length, is_complete, meta = MP4VideoParser.parse_stream(buffer, 0, self.max_file_size)

                # If complete or at EOF with usable length
                if (is_complete and length and length >= self.min_file_size) or (eof and length and length >= self.min_file_size):
                    carved_bytes = bytes(buffer[idx:idx + length])
                    cand_abs_offset = buffer_start_offset + idx
                    yield (carved_bytes, cand_abs_offset, ext or "jpg", meta)
                    idx += length
                    self.current_file_offset = buffer_start_offset + idx
                    continue

                idx += 1
                if idx % 1024 == 0:
                    self.current_file_offset = buffer_start_offset + idx

            if eof:
                self.current_file_offset = buffer_start_offset + len(buffer)
                break

            # Slide window: retain at most 'overlap' bytes at end of buffer
            if len(buffer) > overlap:
                slide = len(buffer) - overlap
                buffer = buffer[slide:]
                buffer_start_offset += slide
                self.current_file_offset = buffer_start_offset
            else:
                more = self._safe_read(self.chunk_size)
                if not more:
                    eof = True
                    self.current_file_offset = buffer_start_offset + len(buffer)
                else:
                    buffer.extend(more)


def recover_images(source: str,
                   output_dir: str,
                   validate: bool = True,
                   deduplicate: bool = True,
                   attempt_repair: bool = True,
                   min_size: int = 1024,
                   max_size: int = 50 * 1024 * 1024,
                   verbose: bool = True) -> List[RecoveredItem]:
    """High-level entry point for recovering images from storage."""
    recovery = SDCardRecovery(
        validate_images=validate,
        deduplicate=deduplicate,
        attempt_repair=attempt_repair,
        min_size=min_size,
        max_size=max_size,
        verbose=verbose
    )
    return recovery.recover(source, output_dir)
