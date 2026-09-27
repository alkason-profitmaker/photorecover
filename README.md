# PhotoRecover 2.0 (Professional Edition)

**PhotoRecover** is a professional-grade photo rescue, damage repair, and AI restoration platform. It is engineered to recover lost photographs, camera RAW files, and videos from formatted or corrupted SD cards, USB drives, memory sticks, and disk images.

Unlike basic signature carvers, PhotoRecover combines **filesystem structure reconstruction (FAT32 & exFAT)**, a **zero-loss streaming carver** that never drops photos crossing chunk boundaries, **damaged JPEG repair**, and an **aspect-ratio preserving AI restoration pipeline**.

---

## What Makes PhotoRecover 2.0 World-Class

1. **Zero-Loss Storage Carving (Fixed Boundary Bug)**:
   - Uses a dynamic sliding-window streaming carver. Photos that span block or sector boundaries (e.g. crossing 64KB, 1MB, or 64MB chunks) are tracked and reconstructed with 100% fidelity.
2. **Filesystem-Aware Reconstruction**:
   - Parses MBR partition tables, FAT32 boot records, and exFAT VBR structures.
   - Extracts deleted directory entries (0xE5 in FAT32, 0x85/0xC0 in exFAT) to restore original filenames, timestamps, and cluster chains.
3. **Multi-Format Media Support**:
   - **JPEG**: Full range of markers (APP0–APP15, COM, SOF0–SOF15, DQT, DHT, DRI).
   - **Camera RAW**: Little-endian and big-endian TIFF containers (Canon CR2, Nikon NEF, Sony ARW, Adobe DNG).
   - **PNG**: Full chunk sequence validation (IHDR -> IDAT -> IEND).
   - **Video**: ISO base media box parsing (MP4, QuickTime MOV) with atom chain verification.
4. **Damaged & Truncated Photo Repair**:
   - Rescues partially written photos or files missing trailing EOI markers (`\xFF\xD9`).
   - Injects standard Huffman and quantization tables where missing, rendering previously unusable photos viewable.
5. **Aspect-Ratio Preserving AI Restoration**:
   - Eliminates distortion bugs (e.g. 4:3 squished into 16:9). Photos scaled to 4K or custom resolutions strictly preserve their original geometry.
   - Powered by Real-ESRGAN / RRDBNet with offline model verification and SHA-256 integrity checks.
6. **Modern Interactive Workstation UI**:
   - Launch `photorecover ui` to access a clean dark-mode local workstation with live sector scanning, real-time counters, thumbnail grid preview, and an interactive Before / After split-slider.
   - Strictly 100% local, offline, and private with zero ads in recovery screens.

---

## Architecture Overview

```
                      Source Media (SD Card / USB / Disk Image)
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
       [Filesystem Engine]                         [Streaming Carver]
      FAT32 / exFAT Parser                      Zero-Boundary Loss Window
    Deleted Directory Entries                    Multi-Format Signatures
    Original Filenames & Clusters               (JPG, PNG, RAW, MP4, MOV)
                    │                                       │
                    └───────────────────┬───────────────────┘
                                        ▼
                            [Damage Repair Engine]
                           Truncated Stream Recovery
                           Header & Huffman Repair
                                        │
                                        ▼
                         [Thumbnail & Preview Cache]
                         Instant Local Web UI Preview
                         Selective Photo Inspection
                                        │
                                        ▼
                     [AI Restoration & Super-Resolution]
                        Aspect-Ratio Preserving Scaling
                        Verified SHA-256 Model Weights
                        Denoising & Detail Enhancement
                                        │
                                        ▼
                            Rescued Photo Gallery
```

---

## Installation

### Standard Installation

```bash
pip install -e .
```

### Full Installation (With PyTorch & Real-ESRGAN AI Acceleration)

```bash
pip install -e ".[ai]"
```

For GPU acceleration (CUDA):
```bash
# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

---

## Quick Start

### 1. Launch the Interactive Workstation (Recommended)

Launch the modern browser UI to visually scan drives, preview thumbnails, and select files to recover:

```bash
photorecover ui
```
Opens automatically on `http://127.0.0.1:8765`.

### 2. Command-Line Deep Recovery

Scan an SD card or disk image file and recover all photos:

```bash
# Recover from disk image
photorecover recover sdcard.img ./recovered/

# Recover from SD card device on Linux
sudo photorecover recover /dev/sdb ./recovered/

# Recover and automatically enhance with AI to 4K
photorecover recover sdcard.img ./recovered/ --enhance
```

### 3. Repair Damaged / Corrupted Photos

```bash
photorecover repair damaged_photo.jpg repaired_photo.jpg
```

### 4. Enhance & Super-Resolve Existing Photos

```bash
photorecover enhance ./photos/ ./enhanced/ --scale 4 --quality ultra
```

### 5. Check AI Model Registry & Checksums

```bash
photorecover models
```

---

## Verification & Test Suite

PhotoRecover 2.0 includes a comprehensive test suite verifying recovery correctness, boundary crossing, aspect ratio preservation, and repair algorithms:

```bash
pytest tests/ -v
```

All 12 automated unit and integration tests pass:
- `test_jpeg_crossing_chunk_boundary`: Verifies zero photos dropped when crossing chunk boundaries.
- `test_aspect_ratio_4_to_3`: Confirms 4:3 photographs are not distorted when upscaled to 4K.
- `test_aspect_ratio_square_1_to_1`: Confirms square photos maintain 1:1 ratio.
- `test_repair_truncated_jpeg`: Verifies recovery of truncated JPEGs missing EOI markers.
- `test_broad_jpeg_marker_detection`: Validates APP0-APP15, COM, and extended markers.
- `test_fat32_vbr_parsing`: Tests FAT32 Volume Boot Record and directory entry extraction.
- `test_model_registry_configurations`: Verifies SHA-256 model checksum enforcement.

---

## License

MIT License. Local, offline, and privacy-preserving.
