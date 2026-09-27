"""
Core Image Enhancement and Restoration Module
Includes denoising, deblurring, contrast enhancement, white balance, and quality assessment.
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from scipy import ndimage
from typing import Optional, Tuple, Union, Dict, Any
from pathlib import Path


class ImageEnhancer:
    """
    Professional photograph enhancement and restoration pipeline.
    Optimized for recovering clarity in degraded or corrupted photo assets.
    """

    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        cascade_file = getattr(cv2.data, 'haarcascades', '') + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_file) if Path(cascade_file).exists() else None

    def load_image(self, image_path: Union[str, Path]) -> np.ndarray:
        """Loads an image from file, auto-transposes EXIF orientation, and returns RGB numpy array."""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if image_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported format: {image_path.suffix}")

        try:
            with Image.open(image_path) as pil_img:
                # Auto-rotate according to camera EXIF orientation tag (e.g. portrait photos)
                transposed = ImageOps.exif_transpose(pil_img)
                return np.array(transposed.convert("RGB"))
        except Exception:
            # Fallback to OpenCV if PIL encounters non-standard stream
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Could not decode image at {image_path}")
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    def save_image(self,
                   image: np.ndarray,
                   output_path: Union[str, Path],
                   quality: int = 95,
                   source_path: Optional[Union[str, Path]] = None):
        """Saves an image to disk with optimal compression and preserved EXIF/ICC profiles."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        exif_bytes = None
        icc_profile = None
        if source_path:
            try:
                with Image.open(source_path) as orig:
                    exif_bytes = orig.info.get("exif")
                    icc_profile = orig.info.get("icc_profile")
            except Exception:
                pass

        ext = output_path.suffix.lower()
        if ext in {'.jpg', '.jpeg', '.png', '.webp'} and (exif_bytes or icc_profile):
            # Use PIL to embed ICC and EXIF profiles
            pil_img = Image.fromarray(image)
            save_kwargs = {}
            if exif_bytes:
                save_kwargs["exif"] = exif_bytes
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile

            if ext in {'.jpg', '.jpeg'}:
                pil_img.save(output_path, format="JPEG", quality=quality, optimize=True, **save_kwargs)
            elif ext == '.png':
                pil_img.save(output_path, format="PNG", optimize=True, **save_kwargs)
            elif ext == '.webp':
                pil_img.save(output_path, format="WEBP", quality=quality, **save_kwargs)
        else:
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if ext in {'.jpg', '.jpeg'}:
                cv2.imwrite(str(output_path), image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
            elif ext == '.png':
                cv2.imwrite(str(output_path), image_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            elif ext == '.webp':
                cv2.imwrite(str(output_path), image_bgr, [cv2.IMWRITE_WEBP_QUALITY, quality])
            else:
                cv2.imwrite(str(output_path), image_bgr)

    def upscale_long_edge(self, image: np.ndarray, long_edge: int = 3840) -> np.ndarray:
        """Scales image so its longest dimension reaches long_edge, preserving aspect ratio."""
        h, w = image.shape[:2]
        current = max(w, h)
        if current >= long_edge:
            return image.copy()
        scale = long_edge / current
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    def assess_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Calculates perceptual quality metrics:
        - Sharpness (Laplacian variance)
        - Contrast score
        - Brightness / Dynamic Range
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        brightness = float(np.mean(gray))
        contrast = float(np.std(gray))

        # Assess blur
        if laplacian_var < 50:
            clarity = "Very Blurry"
        elif laplacian_var < 150:
            clarity = "Slightly Soft"
        elif laplacian_var < 500:
            clarity = "Good Clarity"
        else:
            clarity = "Ultra Sharp"

        return {
            "sharpness_score": round(laplacian_var, 1),
            "clarity_label": clarity,
            "brightness": round(brightness, 1),
            "contrast": round(contrast, 1)
        }

    def denoise(self, image: np.ndarray, strength: int = 8) -> np.ndarray:
        """Removes sensor grain and noise using Non-local Means or bilateral filter."""
        if strength <= 0:
            return image
        try:
            return cv2.fastNlMeansDenoisingColored(
                image, None,
                float(strength),
                float(strength),
                7, 21
            )
        except Exception:
            return cv2.bilateralFilter(image, d=7, sigmaColor=float(strength * 4), sigmaSpace=float(strength * 4))

    def unsharp_mask(self, image: np.ndarray, sigma: float = 1.0,
                      strength: float = 1.2, threshold: int = 0) -> np.ndarray:
        """High-precision unsharp masking for edge restoration."""
        blurred = cv2.GaussianBlur(image, (0, 0), sigma)
        sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)

        if threshold > 0:
            diff = np.abs(image.astype(np.int32) - blurred.astype(np.int32))
            low_contrast_mask = diff < threshold
            sharpened[low_contrast_mask] = image[low_contrast_mask]

        return np.clip(sharpened, 0, 255).astype(np.uint8)

    def enhance_contrast(self, image: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
        """Adaptive contrast enhancement using CLAHE in LAB space."""
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        enhanced_lab = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

    def auto_white_balance(self, image: np.ndarray) -> np.ndarray:
        """White balance correction using Gray World algorithm."""
        result = image.astype(np.float32)
        avg_r = np.mean(result[:, :, 0]) or 1.0
        avg_g = np.mean(result[:, :, 1]) or 1.0
        avg_b = np.mean(result[:, :, 2]) or 1.0

        avg_gray = (avg_r + avg_g + avg_b) / 3.0

        result[:, :, 0] = np.clip(result[:, :, 0] * (avg_gray / avg_r), 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * (avg_gray / avg_g), 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * (avg_gray / avg_b), 0, 255)

        return result.astype(np.uint8)

    def remove_jpeg_artifacts(self, image: np.ndarray) -> np.ndarray:
        """Smooths 8x8 DCT compression block boundaries."""
        ycrcb = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        y = cv2.bilateralFilter(y, 9, 50, 50)
        cr = cv2.bilateralFilter(cr, 9, 50, 50)
        cb = cv2.bilateralFilter(cb, 9, 50, 50)

        enhanced = cv2.merge([y, cr, cb])
        return cv2.cvtColor(enhanced, cv2.COLOR_YCrCb2RGB)

    def super_resolve_lanczos(self, image: np.ndarray, scale: float = 2.0) -> np.ndarray:
        """High-precision Lanczos-4 geometric super-resolution."""
        h, w = image.shape[:2]
        new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_LANCZOS4)

    def detect_faces(self, image: np.ndarray) -> list:
        """Detects faces in photograph and returns bounding boxes (x, y, w, h)."""
        if self.face_cascade is None:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

    def enhance_faces(self, image: np.ndarray, faces: Optional[list] = None) -> np.ndarray:
        """Applies selective detail refinement and gentle skin denoising to facial regions."""
        if faces is None:
            faces = self.detect_faces(image)
        if not faces:
            return image

        result = image.copy()
        for (x, y, w, h) in faces:
            pad_x = int(w * 0.1)
            pad_y = int(h * 0.1)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(image.shape[1], x + w + pad_x)
            y2 = min(image.shape[0], y + h + pad_y)

            roi = result[y1:y2, x1:x2]
            smoothed_roi = cv2.bilateralFilter(roi, d=5, sigmaColor=25, sigmaSpace=25)
            sharpened_roi = self.unsharp_mask(smoothed_roi, sigma=0.8, strength=0.6)
            result[y1:y2, x1:x2] = sharpened_roi

        return result

    def auto_dynamic_range(self, image: np.ndarray) -> np.ndarray:
        """
        Intelligently recovers shadow and midtone details without blowing highlights.
        Adapts gamma and luminance CLAHE based on the photo's dynamic range histogram.
        """
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        l_float = l.astype(np.float32) / 255.0
        median_lum = float(np.median(l_float))

        # Adaptive shadow lift curve
        if median_lum < 0.45:
            gamma = max(0.65, median_lum / 0.5)
            l_lifted = np.power(l_float, gamma) * 255.0
            l_base = np.clip(l_lifted, 0, 255).astype(np.uint8)
        else:
            l_base = l

        # Balanced CLAHE for fine local contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l_base)

        merged_lab = cv2.merge([l_clahe, a, b])
        return cv2.cvtColor(merged_lab, cv2.COLOR_LAB2RGB)

    def restore_color_vibrance(self, image: np.ndarray, factor: float = 1.25) -> np.ndarray:
        """
        Smart vibrance boost for faded photographs.
        Boosts muted colors while protecting already saturated areas and skin tones.
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
        h, s, v = cv2.split(hsv)

        # Inverted saturation weighting: low saturated pixels get more boost
        vibrance_weight = 1.0 + (factor - 1.0) * (1.0 - (s / 255.0))
        s_boosted = np.clip(s * vibrance_weight, 0, 255)

        hsv_boosted = cv2.merge([h, s_boosted, v]).astype(np.uint8)
        return cv2.cvtColor(hsv_boosted, cv2.COLOR_HSV2RGB)

    def studio_photo_restore(self,
                             image: np.ndarray,
                             enhance_portrait: bool = True,
                             auto_exposure: bool = True,
                             denoise: bool = True,
                             super_resolve_scale: float = 1.0) -> np.ndarray:
        """
        World-class photographic restoration master pipeline.
        Transforms degraded, faded, or low-light recovered photos into crisp, studio-grade photographs.
        """
        result = image.copy()

        # Step 1: Denoise sensor grain
        if denoise:
            result = self.denoise(result, strength=7)

        # Step 2: Remove JPEG DCT block artifacts
        result = self.remove_jpeg_artifacts(result)

        # Step 3: Color balance normalization
        result = self.auto_white_balance(result)

        # Step 4: Shadow and dynamic range recovery
        if auto_exposure:
            result = self.auto_dynamic_range(result)

        # Step 5: Color vibrance restoration
        result = self.restore_color_vibrance(result, factor=1.2)

        # Step 6: Portrait facial refinement
        if enhance_portrait:
            result = self.enhance_faces(result)

        # Step 7: Micro-contrast edge sharpening
        result = self.unsharp_mask(result, sigma=1.0, strength=1.1, threshold=3)

        # Step 8: Aspect-ratio preserving super-resolution
        if super_resolve_scale > 1.0:
            result = self.super_resolve_lanczos(result, scale=super_resolve_scale)

        return result

    def full_enhancement_pipeline(self, image: np.ndarray,
                                   denoise_strength: int = 8,
                                   sharpen_strength: float = 1.2,
                                   contrast_clip: float = 2.0,
                                   saturation: float = 1.1,
                                   upscale: float = 1.0,
                                   restore_faces: bool = True) -> np.ndarray:
        """
        Complete sequential restoration pipeline:
        Denoise -> De-artifact -> White Balance -> Contrast -> Face Enhancement -> Upscale -> Sharpen -> Saturation
        """
        enhanced = self.denoise(image, strength=denoise_strength)
        enhanced = self.remove_jpeg_artifacts(enhanced)
        enhanced = self.auto_white_balance(enhanced)
        enhanced = self.enhance_contrast(enhanced, clip_limit=contrast_clip)

        if restore_faces:
            enhanced = self.enhance_faces(enhanced)

        if upscale > 1.0:
            enhanced = self.super_resolve_lanczos(enhanced, scale=upscale)

        enhanced = self.unsharp_mask(enhanced, sigma=1.0, strength=sharpen_strength)

        if saturation != 1.0:
            pil_img = Image.fromarray(enhanced)
            enhancer = ImageEnhance.Color(pil_img)
            enhanced = np.array(enhancer.enhance(saturation))

        return enhanced

    def get_image_info(self, image: np.ndarray) -> dict:
        """Returns dimensional, resolution category, and quality statistics."""
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1
        megapixels = (height * width) / 1_000_000

        if width >= 3840 or height >= 2160:
            res_cat = "4K Ultra HD"
        elif width >= 2560 or height >= 1440:
            res_cat = "2K QHD"
        elif width >= 1920 or height >= 1080:
            res_cat = "Full HD"
        elif width >= 1280 or height >= 720:
            res_cat = "HD"
        else:
            res_cat = "SD"

        quality = self.assess_quality(image)

        return {
            "width": width,
            "height": height,
            "channels": channels,
            "megapixels": round(megapixels, 2),
            "resolution_category": res_cat,
            "quality": quality
        }
