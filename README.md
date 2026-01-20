# PhotoRecover

Complete solution for recovering images from formatted SD cards and enhancing them to HD/4K quality using AI-powered upscaling.

## Features

- **SD Card Recovery**: Recover JPEG images from formatted/corrupted SD cards
- **Duplicate Detection**: Automatically skip duplicate images using content hashing
- **Image Validation**: Only recover complete, valid images
- **AI-Powered Upscaling**: Uses Real-ESRGAN for state-of-the-art 4x super-resolution
- **Multi-Stage Enhancement**: Denoising, sharpening, contrast enhancement, and more
- **Batch Processing**: Process entire directories of images
- **Multiple Resolutions**: HD, Full HD, 2K, 4K, and 8K support

## Installation

### Basic Installation

```bash
pip install -e .
```

### Full Installation (With AI Upscaling)

```bash
pip install -e ".[ai]"
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### GPU Support (Recommended for AI)

```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## Quick Start

### Complete Recovery Pipeline (Recommended)

Recover images from your SD card and enhance them to 4K in one step:

```bash
# From a disk image file
photorecover full-recovery sdcard.img ./output/ --quality ultra

# From SD card device (Linux - requires root)
sudo photorecover full-recovery /dev/sdb ./output/ --quality ultra
```

### Step 1: Recover Images from SD Card

```bash
# Recover from disk image
photorecover recover sdcard.img ./recovered/

# Recover from SD card (Linux)
sudo photorecover recover /dev/sdb ./recovered/

# Recover with enhancement
photorecover recover sdcard.img ./recovered/ --enhance --quality ultra
```

### Step 2: Enhance Recovered Images

```bash
# Enhance to 4K
photorecover enhance ./recovered/ ./enhanced_4k/ --quality ultra --scale 4

# Or upscale to specific resolution
photorecover upscale ./recovered/ ./upscaled/ --resolution 4k
```

## Commands

### `recover`

Recover JPEG images from formatted SD cards or disk images.

```bash
photorecover recover SOURCE OUTPUT_DIR [OPTIONS]

Options:
  -m, --min-size INTEGER      Minimum image size in KB (default: 10)
  -M, --max-size INTEGER      Maximum image size in MB (default: 50)
  --no-validate               Skip image validation (faster)
  --no-dedupe                 Don't skip duplicate images
  -e, --enhance               Also enhance images to 4K after recovery
  -q, --quality [fast|balanced|high|ultra]
                              Enhancement quality (with --enhance)
```

**Examples:**

```bash
# Basic recovery from disk image
photorecover recover sdcard.img ./recovered/

# Recovery from SD card (Linux - run as root)
sudo photorecover recover /dev/sdb ./recovered/

# Recover and enhance in one step
photorecover recover sdcard.img ./recovered/ --enhance --quality ultra

# Quick recovery without validation
photorecover recover sdcard.img ./recovered/ --no-validate

# Recover smaller images (thumbnails)
photorecover recover sdcard.img ./recovered/ --min-size 1
```

### `full-recovery`

Complete pipeline: recover + enhance in one command.

```bash
photorecover full-recovery SOURCE OUTPUT_DIR [OPTIONS]

Options:
  -q, --quality [fast|balanced|high|ultra]
                              Enhancement quality preset (default: ultra)
```

### `enhance`

Enhance images with denoising, sharpening, and upscaling.

```bash
photorecover enhance INPUT OUTPUT [OPTIONS]

Options:
  -s, --scale [2|4]           Upscaling factor (default: 4)
  -q, --quality [fast|balanced|high|ultra]
                              Enhancement preset (default: high)
  -d, --denoise INTEGER       Denoising strength 0-20 (default: 8)
  --sharpen FLOAT             Sharpening strength 0.0-3.0 (default: 1.2)
  --contrast FLOAT            Contrast enhancement 0.5-4.0 (default: 2.0)
  --ai / --no-ai              Use AI upscaling (default: enabled)
  --gpu INTEGER               GPU device ID, -1 for CPU (default: 0)
```

### `upscale`

Upscale images to a specific resolution.

```bash
photorecover upscale INPUT OUTPUT [OPTIONS]

Options:
  -r, --resolution [hd|fullhd|2k|4k|8k]
                              Target resolution (default: 4k)

Resolutions:
  hd      - 1280x720
  fullhd  - 1920x1080
  2k      - 2560x1440
  4k      - 3840x2160
  8k      - 7680x4320
```

### `info`

Display information about an image.

```bash
photorecover info IMAGE_PATH
```

### `models`

List available AI upscaling models.

```bash
photorecover models
```

## How to Create a Disk Image

If you can't access the SD card directly, create a disk image first:

**Linux:**
```bash
# Find your SD card device
lsblk

# Create disk image (replace sdX with your device)
sudo dd if=/dev/sdX of=sdcard.img bs=4M status=progress

# Then recover from the image
photorecover recover sdcard.img ./recovered/
```

**Windows:**
Use [Win32 Disk Imager](https://sourceforge.net/projects/win32diskimager/) to create an image file.

**macOS:**
```bash
# Find your SD card device
diskutil list

# Create disk image (replace diskX with your device)
sudo dd if=/dev/diskX of=sdcard.img bs=4m

# Then recover from the image
photorecover recover sdcard.img ./recovered/
```

## Quality Presets

| Preset   | Denoise | Sharpen | Contrast | Best For |
|----------|---------|---------|----------|----------|
| fast     | 5       | 0.8     | 1.5      | Quick preview |
| balanced | 8       | 1.0     | 2.0      | General use |
| high     | 10      | 1.2     | 2.0      | Important photos |
| ultra    | 12      | 1.5     | 2.5      | Maximum quality |

## Python API

### Recovery

```python
from photorecover import SDCardRecovery, recover_images

# Simple recovery
recovered_files = recover_images(
    source="sdcard.img",
    output_dir="./recovered/",
    validate=True,
    deduplicate=True
)

# Advanced recovery with custom settings
recovery = SDCardRecovery(
    validate_images=True,
    deduplicate=True,
    min_size=10 * 1024,      # 10KB minimum
    max_size=50 * 1024 * 1024,  # 50MB maximum
    verbose=True
)

files = recovery.recover_from_file("sdcard.img", "./recovered/")
print(recovery.stats)  # View recovery statistics
```

### Enhancement

```python
from photorecover import ImageEnhancer, AIUpscaler

enhancer = ImageEnhancer()
upscaler = AIUpscaler(gpu_id=0)

# Load and enhance
image = enhancer.load_image("recovered_001.jpg")

enhanced = enhancer.full_enhancement_pipeline(
    image,
    denoise_strength=12,
    sharpen_strength=1.5,
    contrast_clip=2.5,
    upscale=1
)

# AI upscale to 4K
result = upscaler.upscale_to_4k(enhanced)

# Save
enhancer.save_image(result, "photo_4k.jpg", quality=95)
```

## Tips for Best Recovery

1. **Don't write to the SD card** - Any new data can overwrite recoverable images
2. **Create a disk image first** - Safer than working directly on the card
3. **Use `--no-validate` for partial recovery** - Gets more images but may include corrupt ones
4. **Lower `--min-size` for thumbnails** - Use `--min-size 1` to recover smaller images
5. **Check duplicates are being skipped** - The tool uses content hashing to avoid duplicates

## Tips for Best Enhancement

1. **For very blurry images**: Use `--quality ultra` with `--denoise 15`
2. **For noisy images**: Increase denoise: `--denoise 15-20`
3. **For maximum sharpness**: Use `--sharpen 2.0`
4. **For fastest processing**: Use `--quality fast` or `--no-ai`

## Supported Formats

- JPEG (.jpg, .jpeg) - Recovery and enhancement
- PNG (.png) - Enhancement only
- BMP (.bmp) - Enhancement only
- TIFF (.tiff) - Enhancement only
- WebP (.webp) - Enhancement only

## System Requirements

- Python 3.8+
- 4GB RAM minimum (8GB+ recommended for 4K)
- For AI upscaling: NVIDIA GPU with 4GB+ VRAM (optional)
- For SD card recovery: Root/admin access may be required

## Troubleshooting

**"Permission denied" error:**
- Linux: Run with `sudo`
- Windows: Run as Administrator

**No images recovered:**
- Try `--no-validate` to include partial images
- Lower `--min-size` value
- Make sure SD card hasn't been overwritten

**AI upscaling not working:**
- Install PyTorch with CUDA support
- Or use `--no-ai` for traditional upscaling

## License

MIT License
