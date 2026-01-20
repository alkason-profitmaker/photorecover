# PhotoRecover

Enhance blurry or low-quality recovered images to HD/4K quality using AI-powered upscaling and professional image enhancement techniques.

## Features

- **AI-Powered Upscaling**: Uses Real-ESRGAN for state-of-the-art 4x super-resolution
- **Multi-Stage Enhancement Pipeline**: Denoising, sharpening, contrast enhancement, and more
- **Batch Processing**: Process entire directories of recovered images
- **Multiple Output Resolutions**: HD, Full HD, 2K, 4K, and 8K support
- **GPU Acceleration**: CUDA support for fast processing
- **Fallback Mode**: High-quality traditional upscaling when AI models aren't available

## Installation

### Basic Installation (Traditional Enhancement)

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

### GPU Support

For GPU acceleration, ensure you have CUDA installed and use the appropriate PyTorch version:

```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## Quick Start

### Enhance a Single Image

```bash
# Basic enhancement with 4x upscaling
photorecover enhance blurry_photo.jpg enhanced_photo.jpg

# High-quality enhancement
photorecover enhance blurry_photo.jpg enhanced_photo.jpg --quality ultra --scale 4
```

### Upscale to 4K Resolution

```bash
# Upscale to 4K
photorecover upscale photo.jpg photo_4k.jpg --resolution 4k

# Upscale to Full HD
photorecover upscale photo.jpg photo_hd.jpg --resolution fullhd
```

### Batch Process Recovered Images

```bash
# Process all images in a directory
photorecover batch ./recovered_photos/ ./enhanced_4k/ --quality ultra

# Or use enhance with directories
photorecover enhance ./recovered/ ./enhanced/ --scale 4 --quality high
```

### Get Image Information

```bash
photorecover info photo.jpg
```

## Commands

### `enhance`

Full enhancement pipeline with denoising, sharpening, contrast enhancement, and upscaling.

```bash
photorecover enhance INPUT OUTPUT [OPTIONS]

Options:
  -s, --scale [2|4]           Upscaling factor (default: 4)
  -q, --quality [fast|balanced|high|ultra]
                              Enhancement quality preset (default: high)
  -d, --denoise INTEGER       Denoising strength 0-20 (default: 8)
  --sharpen FLOAT             Sharpening strength 0.0-3.0 (default: 1.2)
  --contrast FLOAT            Contrast enhancement 0.5-4.0 (default: 2.0)
  --ai / --no-ai              Use AI upscaling (default: enabled)
  --gpu INTEGER               GPU device ID, -1 for CPU (default: 0)
  -f, --format [jpg|png|webp] Output format
```

### `upscale`

Upscale images to a specific resolution using AI.

```bash
photorecover upscale INPUT OUTPUT [OPTIONS]

Options:
  -r, --resolution [hd|fullhd|2k|4k|8k]
                              Target resolution (default: 4k)
  --gpu INTEGER               GPU device ID, -1 for CPU (default: 0)

Resolutions:
  hd      - 1280x720
  fullhd  - 1920x1080
  2k      - 2560x1440
  4k      - 3840x2160
  8k      - 7680x4320
```

### `batch`

Batch process all images with optimal settings.

```bash
photorecover batch INPUT_DIR OUTPUT_DIR [OPTIONS]

Options:
  -q, --quality [fast|balanced|high|ultra]
                              Enhancement quality preset (default: high)
```

### `info`

Display information about an image.

```bash
photorecover info IMAGE_PATH
```

### `models`

List available AI upscaling models and their status.

```bash
photorecover models
```

## Quality Presets

| Preset   | Denoise | Sharpen | Contrast | Best For |
|----------|---------|---------|----------|----------|
| fast     | 5       | 0.8     | 1.5      | Quick preview, large batches |
| balanced | 8       | 1.0     | 2.0      | General use |
| high     | 10      | 1.2     | 2.0      | Important photos |
| ultra    | 12      | 1.5     | 2.5      | Maximum quality |

## Python API

You can also use PhotoRecover as a Python library:

```python
from photorecover import ImageEnhancer, AIUpscaler

# Initialize
enhancer = ImageEnhancer()
upscaler = AIUpscaler(gpu_id=0)  # Use gpu_id=None for CPU

# Load and enhance image
image = enhancer.load_image("blurry_photo.jpg")

# Apply full enhancement pipeline
enhanced = enhancer.full_enhancement_pipeline(
    image,
    denoise_strength=10,
    sharpen_strength=1.2,
    contrast_clip=2.0,
    upscale=1  # Don't upscale in pipeline
)

# AI upscale to 4K
result = upscaler.upscale_to_4k(enhanced)

# Or upscale to specific resolution
result = upscaler.upscale_to_resolution(enhanced, 3840, 2160)

# Save
enhancer.save_image(result, "enhanced_4k.jpg", quality=95)
```

### Individual Enhancement Functions

```python
from photorecover import ImageEnhancer

enhancer = ImageEnhancer()
image = enhancer.load_image("photo.jpg")

# Denoise
denoised = enhancer.denoise(image, strength=10)

# Sharpen
sharpened = enhancer.unsharp_mask(image, sigma=1.0, strength=1.5)

# Enhance contrast
contrasted = enhancer.enhance_contrast(image, clip_limit=2.0)

# Auto white balance
balanced = enhancer.auto_white_balance(image)

# Remove JPEG artifacts
cleaned = enhancer.remove_jpeg_artifacts(image)

# Basic upscaling (no AI)
upscaled = enhancer.super_resolve_lanczos(image, scale=4)
```

## Tips for Best Results

1. **For very blurry images**: Use `--quality ultra` with `--denoise 15`
2. **For noisy/grainy images**: Increase denoise strength: `--denoise 15-20`
3. **For faded colors**: The pipeline includes auto white balance and saturation boost
4. **For maximum sharpness**: Use `--sharpen 2.0` (may increase noise)
5. **For fastest processing**: Use `--quality fast` or `--no-ai`

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff)
- WebP (.webp)

## System Requirements

- Python 3.8+
- 4GB RAM minimum (8GB+ recommended for 4K)
- For AI upscaling: NVIDIA GPU with 4GB+ VRAM (optional, CPU fallback available)

## License

MIT License
