"""
Unit Test: FAT32 Filesystem Parser
Tests parsing synthetic FAT32 Volume Boot Record and deleted directory entry scanning.
"""

import struct
from io import BytesIO
from photorecover.filesystem import FAT32Parser, FilesystemFile


def test_fat32_vbr_parsing():
    """Builds a minimal valid FAT32 VBR and verifies parser extracts geometry."""
    vbr = bytearray(512)
    vbr[0:3] = b'\xeb\x58\x90'  # JMP
    vbr[3:11] = b'MSDOS5.0'

    # BPB fields
    struct.pack_into("<H", vbr, 11, 512)   # 512 bytes per sector
    vbr[13] = 8                            # 8 sectors per cluster (4KB)
    struct.pack_into("<H", vbr, 14, 32)    # 32 reserved sectors
    vbr[16] = 2                            # 2 FATs
    struct.pack_into("<I", vbr, 36, 1024)  # 1024 sectors per FAT
    struct.pack_into("<I", vbr, 44, 2)     # Root cluster 2
    vbr[510:512] = b'\x55\xaa'             # Signature

    stream = BytesIO(bytes(vbr) + b'\x00' * (512 * 32))  # Add minimal space
    parser = FAT32Parser(stream)

    assert parser.is_valid is True
    assert parser.bytes_per_sec == 512
    assert parser.sec_per_cluster == 8
    assert parser.root_cluster == 2
    assert parser.cluster_heap_offset > 0
