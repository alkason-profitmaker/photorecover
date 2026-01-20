"""
Command-line interface for PhotoRecover image enhancement tool.
"""

import os
import sys
import click
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

from .enhancer import ImageEnhancer
from .upscaler import AIUpscaler


def print_banner():
    """Print the PhotoRecover banner."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   {Fore.WHITE}██████╗ ██╗  ██╗ ██████╗ ████████╗ ██████╗{Fore.CYAN}                  ║
║   {Fore.WHITE}██╔══██╗██║  ██║██╔═══██╗╚══██╔══╝██╔═══██╗{Fore.CYAN}                 ║
║   {Fore.WHITE}██████╔╝███████║██║   ██║   ██║   ██║   ██║{Fore.CYAN}                 ║
║   {Fore.WHITE}██╔═══╝ ██╔══██║██║   ██║   ██║   ██║   ██║{Fore.CYAN}                 ║
║   {Fore.WHITE}██║     ██║  ██║╚██████╔╝   ██║   ╚██████╔╝{Fore.CYAN}                 ║
║   {Fore.WHITE}╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝{Fore.CYAN}                  ║
║                                                                ║
║   {Fore.YELLOW}██████╗ ███████╗ ██████╗ ██████╗ ██╗   ██╗███████╗██████╗{Fore.CYAN}  ║
║   {Fore.YELLOW}██╔══██╗██╔════╝██╔════╝██╔═══██╗██║   ██║██╔════╝██╔══██╗{Fore.CYAN} ║
║   {Fore.YELLOW}██████╔╝█████╗  ██║     ██║   ██║██║   ██║█████╗  ██████╔╝{Fore.CYAN} ║
║   {Fore.YELLOW}██╔══██╗██╔══╝  ██║     ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗{Fore.CYAN} ║
║   {Fore.YELLOW}██║  ██║███████╗╚██████╗╚██████╔╝ ╚████╔╝ ███████╗██║  ██║{Fore.CYAN} ║
║   {Fore.YELLOW}╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝{Fore.CYAN} ║
║                                                                ║
║        {Fore.GREEN}Recover & Enhance Your Precious Memories to 4K{Fore.CYAN}        ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def print_success(message: str):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print error message."""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print info message."""
    print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")


@click.group()
@click.version_option(version="1.0.0", prog_name="PhotoRecover")
def cli():
    """
    PhotoRecover - Enhance blurry recovered images to HD/4K quality.

    Recover your precious memories from formatted SD cards with professional
    quality enhancement and AI-powered upscaling.
    """
    pass


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--scale', '-s', default=4, type=click.Choice(['2', '4']),
              help='Upscaling factor (2x or 4x)')
@click.option('--quality', '-q', default='high',
              type=click.Choice(['fast', 'balanced', 'high', 'ultra']),
              help='Enhancement quality preset')
@click.option('--denoise', '-d', default=8, type=click.IntRange(0, 20),
              help='Denoising strength (0-20)')
@click.option('--sharpen', default=1.2, type=click.FloatRange(0.0, 3.0),
              help='Sharpening strength (0.0-3.0)')
@click.option('--contrast', default=2.0, type=click.FloatRange(0.5, 4.0),
              help='Contrast enhancement (0.5-4.0)')
@click.option('--ai/--no-ai', default=True,
              help='Use AI upscaling (requires GPU for best performance)')
@click.option('--gpu', default=0, type=int,
              help='GPU device ID (-1 for CPU)')
@click.option('--format', '-f', default=None,
              type=click.Choice(['jpg', 'png', 'webp']),
              help='Output format (default: same as input)')
def enhance(input_path, output_path, scale, quality, denoise, sharpen,
            contrast, ai, gpu, format):
    """
    Enhance a single image or directory of images.

    INPUT_PATH: Path to image file or directory containing images
    OUTPUT_PATH: Path to save enhanced image(s)

    Examples:

        photorecover enhance photo.jpg enhanced_photo.jpg

        photorecover enhance ./recovered/ ./enhanced/ --scale 4 --quality ultra

        photorecover enhance blurry.png sharp.png --denoise 15 --sharpen 2.0
    """
    print_banner()

    input_path = Path(input_path)
    output_path = Path(output_path)

    # Quality presets
    presets = {
        'fast': {'denoise': 5, 'sharpen': 0.8, 'contrast': 1.5},
        'balanced': {'denoise': 8, 'sharpen': 1.0, 'contrast': 2.0},
        'high': {'denoise': 10, 'sharpen': 1.2, 'contrast': 2.0},
        'ultra': {'denoise': 12, 'sharpen': 1.5, 'contrast': 2.5}
    }

    # Apply preset if not overridden
    preset = presets[quality]
    if denoise == 8:  # Default value
        denoise = preset['denoise']
    if sharpen == 1.2:  # Default value
        sharpen = preset['sharpen']
    if contrast == 2.0:  # Default value
        contrast = preset['contrast']

    # Initialize enhancer and upscaler
    enhancer = ImageEnhancer()
    gpu_id = gpu if gpu >= 0 else None
    upscaler = AIUpscaler(gpu_id=gpu_id) if ai else None

    # Check AI status
    if ai:
        status = upscaler.get_status()
        if status['ai_available']:
            print_success(f"AI upscaling enabled (GPU: {'Yes' if status['gpu_enabled'] else 'No'})")
        else:
            print_warning(f"AI model not available: {status['error']}")
            print_info("Falling back to high-quality traditional upscaling")

    scale = int(scale)

    # Process single file or directory
    if input_path.is_file():
        images = [input_path]
        if output_path.suffix == '':
            output_path.mkdir(parents=True, exist_ok=True)
    else:
        images = []
        for ext in enhancer.supported_formats:
            images.extend(input_path.glob(f'*{ext}'))
            images.extend(input_path.glob(f'*{ext.upper()}'))
        images = sorted(set(images))
        output_path.mkdir(parents=True, exist_ok=True)

    if not images:
        print_error("No supported images found!")
        return

    print_info(f"Found {len(images)} image(s) to process")
    print_info(f"Settings: Scale={scale}x, Denoise={denoise}, Sharpen={sharpen}, Contrast={contrast}")
    print()

    # Process images
    success_count = 0
    for img_path in tqdm(images, desc="Enhancing images", unit="img"):
        try:
            # Load image
            image = enhancer.load_image(img_path)
            original_info = enhancer.get_image_info(image)

            # Apply enhancement pipeline
            enhanced = enhancer.full_enhancement_pipeline(
                image,
                denoise_strength=denoise,
                sharpen_strength=sharpen,
                contrast_clip=contrast,
                upscale=1  # We'll handle upscaling separately
            )

            # Apply AI upscaling if enabled
            if ai and upscaler:
                enhanced = upscaler.upscale(enhanced, scale=scale)
            else:
                enhanced = enhancer.super_resolve_lanczos(enhanced, scale=scale)

            # Determine output path
            if output_path.is_dir():
                out_ext = f".{format}" if format else img_path.suffix
                out_file = output_path / f"{img_path.stem}_enhanced{out_ext}"
            else:
                out_file = output_path

            # Save enhanced image
            enhancer.save_image(enhanced, out_file, quality=95)

            # Print info
            enhanced_info = enhancer.get_image_info(enhanced)
            tqdm.write(f"  {img_path.name}: {original_info['width']}x{original_info['height']} "
                       f"→ {enhanced_info['width']}x{enhanced_info['height']} "
                       f"({enhanced_info['resolution_category']})")

            success_count += 1

        except Exception as e:
            print_error(f"Failed to process {img_path.name}: {e}")

    print()
    print_success(f"Successfully enhanced {success_count}/{len(images)} images")
    print_info(f"Output saved to: {output_path}")


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--resolution', '-r', default='4k',
              type=click.Choice(['hd', 'fullhd', '2k', '4k', '8k']),
              help='Target resolution')
@click.option('--gpu', default=0, type=int,
              help='GPU device ID (-1 for CPU)')
def upscale(input_path, output_path, resolution, gpu):
    """
    Upscale images to a specific resolution using AI.

    INPUT_PATH: Path to image file or directory
    OUTPUT_PATH: Path to save upscaled image(s)

    Resolutions:
        hd     - 1280x720
        fullhd - 1920x1080
        2k     - 2560x1440
        4k     - 3840x2160
        8k     - 7680x4320

    Examples:

        photorecover upscale photo.jpg photo_4k.jpg --resolution 4k

        photorecover upscale ./photos/ ./photos_4k/ -r 4k
    """
    print_banner()

    resolutions = {
        'hd': (1280, 720),
        'fullhd': (1920, 1080),
        '2k': (2560, 1440),
        '4k': (3840, 2160),
        '8k': (7680, 4320)
    }

    target_width, target_height = resolutions[resolution]

    input_path = Path(input_path)
    output_path = Path(output_path)

    enhancer = ImageEnhancer()
    gpu_id = gpu if gpu >= 0 else None
    upscaler = AIUpscaler(gpu_id=gpu_id)

    status = upscaler.get_status()
    if status['ai_available']:
        print_success(f"AI upscaling enabled (Model: {status['model_name']})")
    else:
        print_warning("Using high-quality fallback upscaling")

    # Gather images
    if input_path.is_file():
        images = [input_path]
        if output_path.suffix == '':
            output_path.mkdir(parents=True, exist_ok=True)
    else:
        images = []
        for ext in enhancer.supported_formats:
            images.extend(input_path.glob(f'*{ext}'))
            images.extend(input_path.glob(f'*{ext.upper()}'))
        images = sorted(set(images))
        output_path.mkdir(parents=True, exist_ok=True)

    if not images:
        print_error("No supported images found!")
        return

    print_info(f"Upscaling {len(images)} image(s) to {resolution.upper()} ({target_width}x{target_height})")
    print()

    success_count = 0
    for img_path in tqdm(images, desc=f"Upscaling to {resolution.upper()}", unit="img"):
        try:
            image = enhancer.load_image(img_path)
            original_info = enhancer.get_image_info(image)

            # Upscale to target resolution
            upscaled = upscaler.upscale_to_resolution(
                image, target_width, target_height, maintain_aspect=True
            )

            # Determine output path
            if output_path.is_dir():
                out_file = output_path / f"{img_path.stem}_{resolution}{img_path.suffix}"
            else:
                out_file = output_path

            enhancer.save_image(upscaled, out_file, quality=95)

            upscaled_info = enhancer.get_image_info(upscaled)
            tqdm.write(f"  {img_path.name}: {original_info['width']}x{original_info['height']} "
                       f"→ {upscaled_info['width']}x{upscaled_info['height']}")

            success_count += 1

        except Exception as e:
            print_error(f"Failed to process {img_path.name}: {e}")

    print()
    print_success(f"Successfully upscaled {success_count}/{len(images)} images to {resolution.upper()}")


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
def info(input_path):
    """
    Display information about an image.

    INPUT_PATH: Path to image file
    """
    input_path = Path(input_path)
    enhancer = ImageEnhancer()

    try:
        image = enhancer.load_image(input_path)
        info = enhancer.get_image_info(image)

        print(f"\n{Fore.CYAN}Image Information:{Style.RESET_ALL}")
        print(f"  File: {input_path.name}")
        print(f"  Size: {info['width']} x {info['height']} pixels")
        print(f"  Megapixels: {info['megapixels']} MP")
        print(f"  Resolution: {info['resolution_category']}")
        print(f"  Channels: {info['channels']}")
        print(f"  Data type: {info['dtype']}")
        print()

        # Suggest enhancement
        if info['resolution_category'] in ['SD', 'HD']:
            print_info("This image would benefit from 4K upscaling!")
            print(f"  Run: photorecover upscale {input_path} output_4k{input_path.suffix} -r 4k")

    except Exception as e:
        print_error(f"Failed to read image: {e}")


@cli.command()
def models():
    """List available AI upscaling models."""
    print(f"\n{Fore.CYAN}Available AI Upscaling Models:{Style.RESET_ALL}\n")

    models = AIUpscaler.get_available_models()
    for model in models:
        print(f"  {Fore.GREEN}{model['name']}{Style.RESET_ALL}")
        print(f"    Scale: {model['scale']}x")
        print(f"    {model['description']}")
        print()

    upscaler = AIUpscaler()
    status = upscaler.get_status()

    print(f"{Fore.CYAN}Current Status:{Style.RESET_ALL}")
    if status['ai_available']:
        print_success(f"AI models are available")
        print(f"  Active model: {status['model_name']}")
        print(f"  GPU enabled: {'Yes' if status['gpu_enabled'] else 'No'}")
    else:
        print_warning("AI models not available")
        print(f"  Reason: {status['error']}")
        print_info("Install with: pip install realesrgan basicsr torch torchvision")


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('--quality', '-q', default='high',
              type=click.Choice(['fast', 'balanced', 'high', 'ultra']),
              help='Enhancement quality preset')
def batch(input_dir, output_dir, quality):
    """
    Batch process all images in a directory with optimal settings.

    This command applies the full enhancement pipeline and 4K upscaling
    to all supported images in the input directory.

    INPUT_DIR: Directory containing recovered images
    OUTPUT_DIR: Directory to save enhanced images

    Examples:

        photorecover batch ./recovered_photos/ ./enhanced_4k/ --quality ultra
    """
    print_banner()

    # Call enhance with directory paths
    from click.testing import CliRunner
    runner = CliRunner()

    args = [
        'enhance',
        input_dir,
        output_dir,
        '--scale', '4',
        '--quality', quality,
        '--ai'
    ]

    # Execute enhance command
    ctx = click.Context(cli)
    ctx.invoke(enhance, input_path=input_dir, output_path=output_dir,
               scale='4', quality=quality, denoise=8, sharpen=1.2,
               contrast=2.0, ai=True, gpu=0, format=None)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
