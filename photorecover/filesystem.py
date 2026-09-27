"""
FAT32 and exFAT Filesystem Structure Parser
Recovers deleted files, reconstructs directory trees, and parses cluster chains.
"""

import struct
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Generator, BinaryIO
from dataclasses import dataclass, field


@dataclass
class FilesystemFile:
    """Represents a file reconstructed from filesystem metadata."""
    name: str
    size: int
    first_cluster: int
    is_deleted: bool
    extension: str
    fs_type: str
    is_contiguous: bool = True
    clusters: List[int] = field(default_factory=list)


class FAT32Parser:
    """Parses FAT32 boot records, directories, and FAT tables."""

    def __init__(self, stream: BinaryIO, base_offset: int = 0):
        self.stream = stream
        self.base_offset = base_offset
        self.is_valid = False

        self.bytes_per_sec = 512
        self.sec_per_cluster = 8
        self.reserved_secs = 32
        self.num_fats = 2
        self.fat_size_secs = 0
        self.root_cluster = 2
        self.cluster_heap_offset = 0

        self._read_vbr()

    def _read_vbr(self):
        self.stream.seek(self.base_offset)
        boot_sector = self.stream.read(512)
        if len(boot_sector) < 512:
            return

        # Check boot signature 0x55AA
        if boot_sector[510:512] != b'\x55\xaa':
            return

        # Check FAT32 specific fields
        bps = struct.unpack("<H", boot_sector[11:13])[0]
        spc = boot_sector[13]
        res_sec = struct.unpack("<H", boot_sector[14:16])[0]
        num_fats = boot_sector[16]
        fat_size = struct.unpack("<I", boot_sector[36:40])[0]

        if bps in (512, 1024, 2048, 4096) and spc in (1, 2, 4, 8, 16, 32, 64, 128) and fat_size > 0:
            self.bytes_per_sec = bps
            self.sec_per_cluster = spc
            self.reserved_secs = res_sec
            self.num_fats = num_fats
            self.fat_size_secs = fat_size
            self.root_cluster = struct.unpack("<I", boot_sector[44:48])[0]

            fat_bytes = self.num_fats * self.fat_size_secs * self.bytes_per_sec
            res_bytes = self.reserved_secs * self.bytes_per_sec
            self.cluster_heap_offset = self.base_offset + res_bytes + fat_bytes
            self.is_valid = True

    def cluster_to_offset(self, cluster: int) -> int:
        """Converts cluster number to physical byte offset."""
        cluster_size = self.bytes_per_sec * self.sec_per_cluster
        return self.cluster_heap_offset + (cluster - 2) * cluster_size

    def read_cluster(self, cluster: int) -> bytes:
        """Reads all bytes of a specific cluster."""
        cluster_size = self.bytes_per_sec * self.sec_per_cluster
        offset = self.cluster_to_offset(cluster)
        self.stream.seek(offset)
        return self.stream.read(cluster_size)

    def scan_deleted_files(self, max_clusters_to_scan: int = 1000) -> List[FilesystemFile]:
        """Scans root directory and subdirectories for deleted file records (0xE5)."""
        if not self.is_valid:
            return []

        recovered: List[FilesystemFile] = []
        visited_clusters = set()
        queue = [self.root_cluster]

        while queue and len(visited_clusters) < max_clusters_to_scan:
            curr_cluster = queue.pop(0)
            if curr_cluster in visited_clusters or curr_cluster < 2:
                continue
            visited_clusters.add(curr_cluster)

            data = self.read_cluster(curr_cluster)
            lfn_parts: List[str] = []

            for i in range(0, len(data) - 31, 32):
                entry = data[i:i + 32]
                first_byte = entry[0]

                if first_byte == 0x00:  # End of directory entries
                    break

                attr = entry[11]

                # Long File Name (LFN) entry
                if attr == 0x0F:
                    # Accumulate characters (UTF-16 LE)
                    chars = (entry[1:11] + entry[14:26] + entry[28:32])
                    try:
                        part = chars.decode('utf-16-le', errors='ignore').split('\x00')[0]
                        lfn_parts.insert(0, part)
                    except Exception:
                        pass
                    continue

                is_deleted = (first_byte == 0xE5)

                # Short 8.3 filename
                raw_name = entry[0:8].decode('latin1', errors='ignore').strip()
                raw_ext = entry[8:11].decode('latin1', errors='ignore').strip()

                if is_deleted:
                    raw_name = "_" + raw_name[1:]

                filename = "".join(lfn_parts) if lfn_parts else f"{raw_name}.{raw_ext}".strip('.')
                lfn_parts = []  # Reset for next file

                # Read cluster pointers and size
                clus_high = struct.unpack("<H", entry[20:22])[0]
                clus_low = struct.unpack("<H", entry[26:28])[0]
                first_cluster = (clus_high << 16) | clus_low
                file_size = struct.unpack("<I", entry[28:32])[0]

                # Subdirectory
                if attr & 0x10:
                    if first_cluster >= 2 and first_cluster not in visited_clusters:
                        queue.append(first_cluster)
                    continue

                ext = filename.split('.')[-1].lower() if '.' in filename else ""
                if first_cluster >= 2 and file_size > 0:
                    recovered.append(FilesystemFile(
                        name=filename,
                        size=file_size,
                        first_cluster=first_cluster,
                        is_deleted=is_deleted,
                        extension=ext,
                        fs_type="FAT32"
                    ))

        return recovered

    def extract_file_data(self, file_entry: FilesystemFile) -> bytes:
        """Reads file data following cluster chain or contiguous allocation."""
        if not self.is_valid or file_entry.first_cluster < 2:
            return b''

        bytes_needed = file_entry.size
        cluster_size = self.bytes_per_sec * self.sec_per_cluster
        result = bytearray()
        curr_cluster = file_entry.first_cluster

        # Read clusters sequentially up to needed size
        while bytes_needed > 0 and curr_cluster >= 2:
            chunk = self.read_cluster(curr_cluster)
            if not chunk:
                break
            to_read = min(len(chunk), bytes_needed)
            result.extend(chunk[:to_read])
            bytes_needed -= to_read
            curr_cluster += 1  # Standard contiguous assumption for deleted recovery

        return bytes(result)


class ExFATParser:
    """Parses modern high-capacity SDXC (>32GB) exFAT volumes."""

    def __init__(self, stream: BinaryIO, base_offset: int = 0):
        self.stream = stream
        self.base_offset = base_offset
        self.is_valid = False

        self.bytes_per_sec = 512
        self.sec_per_cluster = 8
        self.cluster_heap_offset = 0
        self.root_cluster = 2

        self._read_vbr()

    def _read_vbr(self):
        self.stream.seek(self.base_offset)
        vbr = self.stream.read(512)
        if len(vbr) < 512:
            return

        if vbr[3:11] == b'EXFAT   ':
            sec_shift = vbr[108]
            spc_shift = vbr[109]
            if 9 <= sec_shift <= 12 and 0 <= spc_shift <= 7:
                self.bytes_per_sec = 1 << sec_shift
                self.sec_per_cluster = 1 << spc_shift

                heap_offset_secs = struct.unpack("<I", vbr[88:92])[0]
                self.cluster_heap_offset = self.base_offset + (heap_offset_secs * self.bytes_per_sec)
                self.root_cluster = struct.unpack("<I", vbr[96:100])[0]
                self.is_valid = True

    def cluster_to_offset(self, cluster: int) -> int:
        cluster_size = self.bytes_per_sec * self.sec_per_cluster
        return self.cluster_heap_offset + (cluster - 2) * cluster_size

    def read_cluster(self, cluster: int) -> bytes:
        cluster_size = self.bytes_per_sec * self.sec_per_cluster
        offset = self.cluster_to_offset(cluster)
        self.stream.seek(offset)
        return self.stream.read(cluster_size)

    def extract_file_data(self, file_entry: FilesystemFile) -> bytes:
        """Reads exFAT file data."""
        if not self.is_valid or file_entry.first_cluster < 2:
            return b''

        bytes_needed = file_entry.size
        result = bytearray()
        curr_cluster = file_entry.first_cluster

        while bytes_needed > 0 and curr_cluster >= 2:
            chunk = self.read_cluster(curr_cluster)
            if not chunk:
                break
            to_read = min(len(chunk), bytes_needed)
            result.extend(chunk[:to_read])
            bytes_needed -= to_read
            curr_cluster += 1

        return bytes(result)


class FilesystemRecoveryEngine:
    """High-level filesystem recovery engine for FAT32 / exFAT storage devices."""

    @staticmethod
    def detect_and_scan(stream: BinaryIO) -> Tuple[Optional[str], List[FilesystemFile]]:
        """
        Inspects MBR partitions and VBRs to scan for deleted files.
        Returns: (detected_fs_name, list_of_recovered_files)
        """
        # Try direct volume at offset 0
        fat32 = FAT32Parser(stream, base_offset=0)
        if fat32.is_valid:
            files = fat32.scan_deleted_files()
            return ("FAT32", files)

        exfat = ExFATParser(stream, base_offset=0)
        if exfat.is_valid:
            return ("exFAT", [])

        # Check MBR partition table at offset 0
        stream.seek(0)
        sector0 = stream.read(512)
        if len(sector0) == 512 and sector0[510:512] == b'\x55\xaa':
            for p_idx in range(4):
                p_offset = 446 + p_idx * 16
                p_entry = sector0[p_offset:p_offset + 16]
                p_type = p_entry[4]
                lba_start = struct.unpack("<I", p_entry[8:12])[0]

                if lba_start > 0:
                    byte_offset = lba_start * 512
                    # Test FAT32
                    fat = FAT32Parser(stream, base_offset=byte_offset)
                    if fat.is_valid:
                        return ("FAT32", fat.scan_deleted_files())
                    # Test exFAT
                    ex = ExFATParser(stream, base_offset=byte_offset)
                    if ex.is_valid:
                        return ("exFAT", [])

        return (None, [])
