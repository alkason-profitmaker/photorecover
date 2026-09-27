"""
PhotoRecover 2.0 - Command-Line Interface
Unified tool for deep photo rescue, filesystem reconstruction, damage repair, and AI restoration.
"""

import os
import sys
import click
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize cross-platform color console
# Configure UTF-8 for console output if supported
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

init()

from .enhancer import ImageEnhancer
from .upscaler import AIUpscaler
from .recovery import SDCardRecovery, RecoveredItem
from .repair import JPEGRepairer
from .models import ModelRegistry
from .gui import start_server


def print_banner():
    """Print the PhotoRecover 2.0 banner with safe encoding fallback."""
    banner = f"""
{Fore.CYAN}+==============================================================+
|   {Fore.WHITE}PHOTORECOVER 2.0 - PROFESSIONAL PHOTO RESCUE & AI RESTORATION{Fore.CYAN} |
|   {Fore.YELLOW}Zero-Loss Carving * FAT32/exFAT Reconstruction * Damaged Repair{Fore.CYAN}   |
+==============================================================+{Style.RESET_ALL}
"""
    try:
        print(banner)
    except Exception:
        print("\n--- PHOTORECOVER 2.0 (PROFESSIONAL EDITION) ---\n")


def print_success(message: str):
    try:
        print(f"{Fore.GREEN}[OK] {message}{Style.RESET_ALL}")
    except Exception:
        print(f"[OK] {message}")


def print_error(message: str):
    try:
        print(f"{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")
    except Exception:
        print(f"[ERROR] {message}")


def print_info(message: str):
    try:
        print(f"{Fore.BLUE}[INFO] {message}{Style.RESET_ALL}")
    except Exception:
        print(f"[INFO] {message}")


def print_warning(message: str):
    try:
        print(f"{Fore.YELLOW}[WARN] {message}{Style.RESET_ALL}")
    except Exception:
        print(f"[WARN] {message}")


@click.group()
@click.version_option(version="2.0.0", prog_name="PhotoRecover")
def cli():
    """
    PhotoRecover 2.0 - Professional Photo Rescue & AI Restoration.

    Capabilities:
    1. Zero-loss storage recovery across chunk boundaries
    2. FAT32/exFAT partition & deleted directory reconstruction
    3. Multi-format support: JPEG, PNG, Camera RAW (CR2/NEF/ARW), MP4/MOV
    4. Truncated & damaged JPEG structural repair
    5. Aspect-ratio preserving AI Super-Resolution & Enhancement
    6. Interactive local Workstation UI with thumbnail preview
    """
    pass


@cli.command()
@click.option('--port', '-p', default=8765, type=int, help='Local server port (default 8765)')
@click.option('--no-browser', is_flag=True, help='Do not launch browser automatically')
def ui(port, no_browser):
    """
    Launch interactive Web GUI Workstation with thumbnail preview.

    Starts a fast local server and opens your browser to review photos,
    filter by type, compare before/after AI restoration, and recover selectively.
    """
    print_banner()
    start_server(port=port, open_browser=not no_browser)


@cli.command()
@click.argument('source', type=click.Path(exists=True))
@click.argument('output_dir', type=click.Path())
@click.option('--fs/--no-fs', default=True, help='Scan FAT32/exFAT filesystem entries (default: True)')
@click.option('--repair/--no-repair', default=True, help='Attempt repair of truncated/corrupted photos')
@click.option('--raw/--no-raw', default=True, help='Carve Camera RAW files (CR2, NEF, ARW, DNG)')
@click.option('--video/--no-video', default=True, help='Carve video files (MP4, MOV)')
@click.option('--dedupe/--no-dedupe', default=True, help='Deduplicate using SHA-256')
@click.option('--enhance', '-e', is_flag=True, help='Automatically apply AI enhancement on recovered photos')
def recover(source, output_dir, fs, repair, raw, video, dedupe, enhance):
    """
    Recover photos and media from storage device, SD card, or disk image.

    SOURCE: Path to storage device (e.g. \\\\.\\E: or /dev/sdb) or disk image (.img/.raw)
    OUTPUT_DIR: Target folder to store recovered media
    """
    print_banner()
    source_path = Path(source)
    out_path = Path(output_dir)

    print_info(f"Source Media:  {source_path}")
    print_info(f"Target Output: {out_path}")
    print_info(f"Engines:       Filesystem={'ON' if fs else 'OFF'} | Raw Carver=ON | Repair={'ON' if repair else 'OFF'}")
    print()

    recovery = SDCardRecovery(
        validate_images=True,
        deduplicate=dedupe,
        attempt_repair=repair,
        include_raw=raw,
        include_video=video,
        verbose=True
    )

    pbar = tqdm(total=source_path.stat().st_size if source_path.is_file() else 0,
                unit='B', unit_scale=True, desc="Deep Scanning")

    def on_progress(p):
        pbar.n = min(p.get("bytes_scanned", 0), pbar.total or p.get("bytes_scanned", 0))
        pbar.refresh()

    items = recovery.recover(
        source_path=str(source_path),
        output_dir=str(out_path),
        scan_filesystem=fs,
        progress_callback=on_progress
    )
    pbar.close()

    print_success(f"Successfully rescued {len(items)} files into {out_path}")

    if enhance and items:
        print()
        print_info("Executing AI Super-Resolution on recovered photographs...")
        enhancer = ImageEnhancer()
        upscaler = AIUpscaler()
        enh_dir = out_path / "enhanced"
        enh_dir.mkdir(parents=True, exist_ok=True)

        for item in tqdm(items, desc="Restoring photos", unit="img"):
            if item.extension in ('jpg', 'jpeg', 'png'):
                try:
                    img = enhancer.load_image(item.path)
                    enhanced = enhancer.full_enhancement_pipeline(img, upscale=1.0)
                    upscaled = upscaler.upscale_to_4k(enhanced)
                    out_f = enh_dir / f"{Path(item.path).stem}_4k.jpg"
                    enhancer.save_image(upscaled, out_f, quality=95)
                except Exception as err:
                    tqdm.write(f"  Enhancement skipped for {item.filename}: {err}")

        print_success(f"Enhanced photographs saved to {enh_dir}")


@cli.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
def repair(image_path, output_path):
    """
    Repair a truncated or corrupted JPEG file.
    """
    print_banner()
    in_file = Path(image_path)
    out_file = Path(output_path)

    raw_data = in_file.read_bytes()
    repaired_data, was_rep, meta = JPEGRepairer.attempt_repair(raw_data)

    if repaired_data:
        out_file.write_bytes(repaired_data)
        print_success(f"Successfully repaired {in_file.name} -> {out_file} (Dimensions: {meta.get('width')}x{meta.get('height')})")
    else:
        print_error(f"Unable to repair {in_file.name}: {meta.get('error')}")


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--scale', '-s', default=4, type=click.Choice(['2', '4']), help='Upscale factor')
@click.option('--quality', '-q', default='high', type=click.Choice(['fast', 'balanced', 'high', 'ultra']))
def enhance(input_path, output_path, scale, quality):
    """
    Enhance clarity, color balance, and resolution of photos.
    """
    print_banner()
    enhancer = ImageEnhancer()
    upscaler = AIUpscaler()

    presets = {
        'fast': {'denoise': 5, 'sharpen': 0.8, 'contrast': 1.5},
        'balanced': {'denoise': 8, 'sharpen': 1.0, 'contrast': 2.0},
        'high': {'denoise': 10, 'sharpen': 1.2, 'contrast': 2.0},
        'ultra': {'denoise': 12, 'sharpen': 1.5, 'contrast': 2.5}
    }
    cfg = presets[quality]

    img = enhancer.load_image(input_path)
    enhanced = enhancer.full_enhancement_pipeline(
        img,
        denoise_strength=cfg['denoise'],
        sharpen_strength=cfg['sharpen'],
        contrast_clip=cfg['contrast'],
        upscale=1.0
    )
    upscaled = upscaler.upscale(enhanced, scale=int(scale))
    enhancer.save_image(upscaled, output_path)
    print_success(f"Enhanced {input_path} -> {output_path}")


@cli.command()
def models():
    """
    List and verify AI Super-Resolution model status.
    """
    print_banner()
    print(f"\n{Fore.CYAN}Registered Super-Resolution Models:{Style.RESET_ALL}\n")
    for name, info in ModelRegistry.MODELS.items():
        cached_path = ModelRegistry.get_model_path(name)
        is_verified = ModelRegistry.verify_file(cached_path, info.get("sha256"))
        status_tag = f"{Fore.GREEN}[Installed & Verified]{Style.RESET_ALL}" if is_verified else f"{Fore.YELLOW}[Not Installed]{Style.RESET_ALL}"
        print(f"  • {Fore.WHITE}{name}{Style.RESET_ALL} (Scale: {info['scale']}x) {status_tag}")
        print(f"    {info['description']}")
        print(f"    Target Hash: {info['sha256']}")
        print()


@cli.command('generate-corpus')
@click.argument('output_path', type=click.Path(), default="benchmark_disk.img")
@click.option('--size-mb', default=4, type=int, help='Size of synthetic disk image in MB')
def generate_corpus_cmd(output_path, size_mb):
    """
    Generate synthetic benchmark disk image with known ground-truth photos.
    Includes boundary-spanning JPEGs, truncated photos, PNGs, and RAW containers.
    """
    from .corpus import create_synthetic_recovery_corpus
    print_banner()
    print_info(f"Generating synthetic {size_mb}MB test disk image: {output_path}...")
    gt = create_synthetic_recovery_corpus(output_path, size_mb=size_mb)
    print_success(f"Generated test disk with {gt['total_embeds']} embedded ground truth files:")
    print(f"  • Intact JPEGs:       {gt['intact_jpegs']}")
    print(f"  • Boundary JPEGs:     {gt['boundary_jpegs']}")
    print(f"  • Truncated JPEGs:    {gt['truncated_jpegs']}")
    print(f"  • PNG Images:         {gt['pngs']}")
    print(f"  • Camera RAW TIFF:    {gt['raw_tiffs']}")
    print_info(f"Test recovery with: photorecover recover {output_path} ./test_recovered/")


def main():
    cli()


if __name__ == '__main__':
    main()
