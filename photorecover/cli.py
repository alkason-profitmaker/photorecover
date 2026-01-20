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
from .recovery import SDCardRecovery


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
@click.version_option(version="1.1.0", prog_name="PhotoRecover")
def cli():
    """
    PhotoRecover - Recover and enhance images from formatted SD cards.

    Complete solution for:
    1. Recovering JPEG images from formatted/corrupted SD cards
    2. Removing duplicates and validating recovered images
    3. Enhancing blurry images to HD/4K quality with AI upscaling
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


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('--min-size', '-m', default=10, type=int,
              help='Minimum image size in KB (default: 10)')
@click.option('--max-size', '-M', default=50, type=int,
              help='Maximum image size in MB (default: 50)')
@click.option('--no-validate', is_flag=True,
              help='Skip image validation (faster but may include corrupt images)')
@click.option('--no-dedupe', is_flag=True,
              help='Do not skip duplicate images')
@click.option('--enhance', '-e', is_flag=True,
              help='Also enhance recovered images to 4K after recovery')
@click.option('--quality', '-q', default='high',
              type=click.Choice(['fast', 'balanced', 'high', 'ultra']),
              help='Enhancement quality (only used with --enhance)')
def recover(source, output_dir, min_size, max_size, no_validate, no_dedupe, enhance, quality):
    """
    Recover JPEG images from a formatted SD card or disk image.

    This command scans raw storage for JPEG file signatures and extracts
    complete, valid images while automatically removing duplicates.

    SOURCE: Path to SD card device (e.g., /dev/sdb) or disk image file
    OUTPUT_DIR: Directory to save recovered images

    Examples:

        # Recover from SD card (Linux - run as root)
        sudo photorecover recover /dev/sdb ./recovered/

        # Recover from disk image file
        photorecover recover sdcard.img ./recovered/

        # Recover and enhance to 4K in one step
        photorecover recover sdcard.img ./recovered/ --enhance --quality ultra

        # Quick recovery without validation
        photorecover recover /dev/sdb ./recovered/ --no-validate

    Notes:

        On Linux, you may need root access to read raw devices:
            sudo photorecover recover /dev/sdb ./recovered/

        On Windows, use disk image files or tools like Win32DiskImager to
        create an image of the SD card first.

        To find your SD card device on Linux:
            lsblk

        To create a disk image:
            sudo dd if=/dev/sdb of=sdcard.img bs=4M status=progress
    """
    print_banner()

    source_path = Path(source)
    output_path = Path(output_dir)

    print_info(f"Source: {source_path}")
    print_info(f"Output: {output_path}")
    print_info(f"Settings: min={min_size}KB, max={max_size}MB, validate={'No' if no_validate else 'Yes'}, dedupe={'No' if no_dedupe else 'Yes'}")
    print()

    # Initialize recovery module
    recovery = SDCardRecovery(
        validate_images=not no_validate,
        deduplicate=not no_dedupe,
        min_size=min_size * 1024,  # Convert KB to bytes
        max_size=max_size * 1024 * 1024,  # Convert MB to bytes
        verbose=True
    )

    # Progress bar for large files
    try:
        total_size = source_path.stat().st_size
        pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Scanning")

        def progress_callback(processed, total):
            pbar.n = min(processed, total)
            pbar.refresh()

        # Run recovery
        recovered_files = recovery.recover_from_file(
            str(source_path),
            str(output_path),
            progress_callback=progress_callback
        )

        pbar.close()

    except PermissionError:
        print_error("Permission denied! Try running with sudo (Linux) or as Administrator (Windows)")
        print_info("  Linux: sudo photorecover recover /dev/sdb ./recovered/")
        return
    except Exception as e:
        print_error(f"Recovery failed: {e}")
        return

    if not recovered_files:
        print_warning("No valid images were recovered.")
        print_info("Tips:")
        print_info("  - Try lowering --min-size (e.g., --min-size 1)")
        print_info("  - Try --no-validate to include partially corrupt images")
        print_info("  - Make sure the SD card hasn't been overwritten")
        return

    print()
    print_success(f"Recovered {len(recovered_files)} images to {output_path}")

    # Optionally enhance recovered images
    if enhance:
        print()
        print_info("Starting image enhancement...")

        enhanced_dir = output_path / "enhanced_4k"
        enhanced_dir.mkdir(parents=True, exist_ok=True)

        # Quality presets
        presets = {
            'fast': {'denoise': 5, 'sharpen': 0.8, 'contrast': 1.5},
            'balanced': {'denoise': 8, 'sharpen': 1.0, 'contrast': 2.0},
            'high': {'denoise': 10, 'sharpen': 1.2, 'contrast': 2.0},
            'ultra': {'denoise': 12, 'sharpen': 1.5, 'contrast': 2.5}
        }
        preset = presets[quality]

        enhancer = ImageEnhancer()
        upscaler = AIUpscaler(gpu_id=0)

        status = upscaler.get_status()
        if status['ai_available']:
            print_success(f"AI upscaling enabled")
        else:
            print_warning("Using fallback upscaling (AI not available)")

        success_count = 0
        for img_path in tqdm(recovered_files, desc="Enhancing images", unit="img"):
            try:
                img_path = Path(img_path)
                image = enhancer.load_image(img_path)

                # Apply enhancement pipeline
                enhanced = enhancer.full_enhancement_pipeline(
                    image,
                    denoise_strength=preset['denoise'],
                    sharpen_strength=preset['sharpen'],
                    contrast_clip=preset['contrast'],
                    upscale=1
                )

                # AI upscale
                enhanced = upscaler.upscale(enhanced, scale=4)

                # Save
                out_file = enhanced_dir / f"{img_path.stem}_4k.jpg"
                enhancer.save_image(enhanced, out_file, quality=95)
                success_count += 1

            except Exception as e:
                tqdm.write(f"  Failed to enhance {img_path.name}: {e}")

        print()
        print_success(f"Enhanced {success_count}/{len(recovered_files)} images to 4K")
        print_info(f"Enhanced images saved to: {enhanced_dir}")


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('--quality', '-q', default='ultra',
              type=click.Choice(['fast', 'balanced', 'high', 'ultra']),
              help='Enhancement quality preset')
def full_recovery(source, output_dir, quality):
    """
    Complete recovery pipeline: recover images and enhance to 4K.

    This is a convenience command that combines recovery and enhancement
    in a single step for the best results.

    SOURCE: Path to SD card device or disk image
    OUTPUT_DIR: Directory to save all output

    The command will create two subdirectories:
        - recovered/    - Original recovered images
        - enhanced_4k/  - 4K enhanced versions

    Examples:

        photorecover full-recovery sdcard.img ./output/ --quality ultra

        sudo photorecover full-recovery /dev/sdb ./output/
    """
    # Simply call recover with --enhance flag
    ctx = click.Context(recover)
    ctx.invoke(recover, source=source, output_dir=output_dir,
               min_size=10, max_size=50, no_validate=False,
               no_dedupe=False, enhance=True, quality=quality)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
