"""
Core image enhancement module with various restoration techniques.
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from scipy import ndimage
from typing import Optional, Tuple, Union
from pathlib import Path


class ImageEnhancer:
    """
    Comprehensive image enhancement class for restoring blurry/degraded images.
    """

    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    def load_image(self, image_path: Union[str, Path]) -> np.ndarray:
        """Load an image from file path."""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if image_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported format: {image_path.suffix}")

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def save_image(self, image: np.ndarray, output_path: Union[str, Path], quality: int = 95):
        """Save an enhanced image to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if output_path.suffix.lower() in {'.jpg', '.jpeg'}:
            cv2.imwrite(str(output_path), image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
        elif output_path.suffix.lower() == '.png':
            cv2.imwrite(str(output_path), image_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        else:
            cv2.imwrite(str(output_path), image_bgr)

    def denoise(self, image: np.ndarray, strength: int = 10) -> np.ndarray:
        """
        Remove noise from image using Non-local Means Denoising.
        Good for removing grain and artifacts from recovered images.
        """
        return cv2.fastNlMeansDenoisingColored(
            image, None,
            h=strength,
            hForColorComponents=strength,
            templateWindowSize=7,
            searchWindowSize=21
        )

    def denoise_advanced(self, image: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """
        Advanced denoising using bilateral filter for edge preservation.
        """
        d = int(9 * strength) if strength > 0.3 else 5
        sigma_color = int(75 * strength + 25)
        sigma_space = int(75 * strength + 25)

        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)

    def sharpen(self, image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Sharpen image to enhance edges and details.
        """
        kernel = np.array([
            [-1, -1, -1],
            [-1, 9 + strength, -1],
            [-1, -1, -1]
        ]) / (1 + strength)

        return cv2.filter2D(image, -1, kernel)

    def unsharp_mask(self, image: np.ndarray, sigma: float = 1.0,
                     strength: float = 1.5, threshold: int = 0) -> np.ndarray:
        """
        Apply unsharp mask for professional-grade sharpening.
        Better for recovering fine details in blurry images.
        """
        blurred = cv2.GaussianBlur(image, (0, 0), sigma)
        sharpened = cv2.addWeighted(image, 1 + strength, blurred, -strength, 0)

        if threshold > 0:
            low_contrast_mask = np.abs(image.astype(float) - blurred.astype(float)) < threshold
            np.copyto(sharpened, image, where=low_contrast_mask)

        return np.clip(sharpened, 0, 255).astype(np.uint8)

    def deblur_wiener(self, image: np.ndarray, noise_var: float = 0.01) -> np.ndarray:
        """
        Wiener deconvolution for motion blur removal.
        """
        result = image.copy().astype(np.float64)

        for i in range(3):
            channel = result[:, :, i]
            f = np.fft.fft2(channel)

            # Simple Wiener filter approximation
            h = np.ones((5, 5)) / 25
            H = np.fft.fft2(h, s=channel.shape)

            # Wiener deconvolution
            H_conj = np.conj(H)
            denominator = np.abs(H) ** 2 + noise_var
            restored = np.fft.ifft2(f * H_conj / denominator)
            result[:, :, i] = np.abs(restored)

        return np.clip(result, 0, 255).astype(np.uint8)

    def enhance_contrast(self, image: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
        """
        Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Great for recovered images with poor contrast.
        """
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)

        enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

    def auto_white_balance(self, image: np.ndarray) -> np.ndarray:
        """
        Automatic white balance correction using Gray World algorithm.
        """
        result = image.copy().astype(np.float32)

        avg_r = np.mean(result[:, :, 0])
        avg_g = np.mean(result[:, :, 1])
        avg_b = np.mean(result[:, :, 2])

        avg_gray = (avg_r + avg_g + avg_b) / 3

        result[:, :, 0] = result[:, :, 0] * (avg_gray / avg_r)
        result[:, :, 1] = result[:, :, 1] * (avg_gray / avg_g)
        result[:, :, 2] = result[:, :, 2] * (avg_gray / avg_b)

        return np.clip(result, 0, 255).astype(np.uint8)

    def adjust_brightness_contrast(self, image: np.ndarray,
                                   brightness: float = 1.0,
                                   contrast: float = 1.0) -> np.ndarray:
        """
        Adjust brightness and contrast of the image.
        """
        pil_image = Image.fromarray(image)

        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(brightness)

        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(contrast)

        return np.array(pil_image)

    def adjust_saturation(self, image: np.ndarray, factor: float = 1.2) -> np.ndarray:
        """
        Adjust color saturation.
        """
        pil_image = Image.fromarray(image)
        enhancer = ImageEnhance.Color(pil_image)
        return np.array(enhancer.enhance(factor))

    def remove_jpeg_artifacts(self, image: np.ndarray) -> np.ndarray:
        """
        Remove JPEG compression artifacts using specialized filtering.
        """
        # Convert to YCrCb for better artifact removal
        ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        # Apply bilateral filter to each channel
        y = cv2.bilateralFilter(y, 9, 75, 75)
        cr = cv2.bilateralFilter(cr, 9, 75, 75)
        cb = cv2.bilateralFilter(cb, 9, 75, 75)

        enhanced = cv2.merge([y, cr, cb])
        return cv2.cvtColor(enhanced, cv2.COLOR_YCrCb2RGB)

    def super_resolve_bicubic(self, image: np.ndarray, scale: int = 2) -> np.ndarray:
        """
        Basic upscaling using bicubic interpolation.
        Fast but lower quality than AI methods.
        """
        height, width = image.shape[:2]
        new_size = (width * scale, height * scale)
        return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)

    def super_resolve_lanczos(self, image: np.ndarray, scale: int = 2) -> np.ndarray:
        """
        High-quality upscaling using Lanczos interpolation.
        Better than bicubic for photo upscaling.
        """
        height, width = image.shape[:2]
        new_size = (width * scale, height * scale)
        return cv2.resize(image, new_size, interpolation=cv2.INTER_LANCZOS4)

    def enhance_details(self, image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Enhance fine details using high-pass filtering technique.
        """
        # Apply Gaussian blur to get low-frequency components
        blurred = cv2.GaussianBlur(image, (0, 0), 3)

        # High-pass filter = original - blurred
        high_pass = cv2.subtract(image, blurred)

        # Add enhanced high-frequency back to original
        enhanced = cv2.addWeighted(image, 1.0, high_pass, strength, 0)

        return np.clip(enhanced, 0, 255).astype(np.uint8)

    def full_enhancement_pipeline(self, image: np.ndarray,
                                  denoise_strength: int = 8,
                                  sharpen_strength: float = 1.2,
                                  contrast_clip: float = 2.0,
                                  saturation: float = 1.1,
                                  upscale: int = 2) -> np.ndarray:
        """
        Complete enhancement pipeline for recovered images.
        Applies all enhancement techniques in optimal order.
        """
        # Step 1: Denoise to remove artifacts
        enhanced = self.denoise(image, strength=denoise_strength)

        # Step 2: Remove JPEG artifacts
        enhanced = self.remove_jpeg_artifacts(enhanced)

        # Step 3: Auto white balance
        enhanced = self.auto_white_balance(enhanced)

        # Step 4: Enhance contrast
        enhanced = self.enhance_contrast(enhanced, clip_limit=contrast_clip)

        # Step 5: Upscale using Lanczos
        if upscale > 1:
            enhanced = self.super_resolve_lanczos(enhanced, scale=upscale)

        # Step 6: Sharpen (after upscaling for best results)
        enhanced = self.unsharp_mask(enhanced, sigma=1.0, strength=sharpen_strength)

        # Step 7: Enhance details
        enhanced = self.enhance_details(enhanced, strength=0.5)

        # Step 8: Adjust saturation
        enhanced = self.adjust_saturation(enhanced, factor=saturation)

        return enhanced

    def get_image_info(self, image: np.ndarray) -> dict:
        """Get image information and statistics."""
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1

        # Calculate megapixels
        megapixels = (height * width) / 1_000_000

        # Determine resolution category
        if width >= 3840 or height >= 2160:
            resolution = "4K Ultra HD"
        elif width >= 2560 or height >= 1440:
            resolution = "2K QHD"
        elif width >= 1920 or height >= 1080:
            resolution = "Full HD"
        elif width >= 1280 or height >= 720:
            resolution = "HD"
        else:
            resolution = "SD"

        return {
            "width": width,
            "height": height,
            "channels": channels,
            "megapixels": round(megapixels, 2),
            "resolution_category": resolution,
            "dtype": str(image.dtype)
        }
