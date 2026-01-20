"""
AI-powered image upscaling module using Real-ESRGAN and other super-resolution models.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Union, Literal
import warnings


class AIUpscaler:
    """
    AI-powered image upscaler using Real-ESRGAN for high-quality 4K upscaling.
    Falls back to traditional methods if AI models are unavailable.
    """

    def __init__(self, model_name: str = "RealESRGAN_x4plus", gpu_id: Optional[int] = 0):
        """
        Initialize the AI upscaler.

        Args:
            model_name: Name of the Real-ESRGAN model to use.
                Options: RealESRGAN_x4plus, RealESRGAN_x4plus_anime_6B,
                         RealESRNet_x4plus, RealESRGAN_x2plus
            gpu_id: GPU device ID. Set to None for CPU mode.
        """
        self.model_name = model_name
        self.gpu_id = gpu_id
        self.upsampler = None
        self._model_loaded = False
        self._load_error = None

        # Model configurations
        self.model_configs = {
            "RealESRGAN_x4plus": {"scale": 4, "model_path": None},
            "RealESRGAN_x4plus_anime_6B": {"scale": 4, "model_path": None},
            "RealESRNet_x4plus": {"scale": 4, "model_path": None},
            "RealESRGAN_x2plus": {"scale": 2, "model_path": None},
        }

    def _load_model(self):
        """Load the Real-ESRGAN model."""
        if self._model_loaded:
            return True

        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet

            if self.model_name == "RealESRGAN_x4plus":
                model = RRDBNet(
                    num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=23, num_grow_ch=32, scale=4
                )
                netscale = 4
                model_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

            elif self.model_name == "RealESRGAN_x4plus_anime_6B":
                model = RRDBNet(
                    num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=6, num_grow_ch=32, scale=4
                )
                netscale = 4
                model_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"

            elif self.model_name == "RealESRGAN_x2plus":
                model = RRDBNet(
                    num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=23, num_grow_ch=32, scale=2
                )
                netscale = 2
                model_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"

            else:
                model = RRDBNet(
                    num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=23, num_grow_ch=32, scale=4
                )
                netscale = 4
                model_url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

            # Determine model path
            model_dir = Path.home() / ".cache" / "photorecover" / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"{self.model_name}.pth"

            self.upsampler = RealESRGANer(
                scale=netscale,
                model_path=str(model_path) if model_path.exists() else model_url,
                model=model,
                tile=0,  # No tiling for smaller images
                tile_pad=10,
                pre_pad=0,
                half=False,  # Use full precision for better quality
                gpu_id=self.gpu_id
            )

            self._model_loaded = True
            return True

        except ImportError as e:
            self._load_error = f"Real-ESRGAN not available: {e}. Using fallback upscaling."
            warnings.warn(self._load_error)
            return False

        except Exception as e:
            self._load_error = f"Failed to load AI model: {e}. Using fallback upscaling."
            warnings.warn(self._load_error)
            return False

    def upscale(self, image: np.ndarray, scale: int = 4,
                outscale: Optional[float] = None) -> np.ndarray:
        """
        Upscale image using AI super-resolution.

        Args:
            image: Input image as numpy array (RGB format)
            scale: Upscaling factor (2 or 4)
            outscale: Final output scale. If None, uses the model's native scale.

        Returns:
            Upscaled image as numpy array
        """
        if outscale is None:
            outscale = float(scale)

        # Try AI upscaling first
        if self._load_model():
            try:
                # Convert RGB to BGR for Real-ESRGAN
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # Upscale
                output_bgr, _ = self.upsampler.enhance(image_bgr, outscale=outscale)

                # Convert back to RGB
                return cv2.cvtColor(output_bgr, cv2.COLOR_BGR2RGB)

            except Exception as e:
                warnings.warn(f"AI upscaling failed: {e}. Using fallback.")

        # Fallback to high-quality traditional upscaling
        return self._fallback_upscale(image, scale)

    def _fallback_upscale(self, image: np.ndarray, scale: int) -> np.ndarray:
        """
        High-quality fallback upscaling using enhanced traditional methods.
        Combines Lanczos interpolation with edge enhancement.
        """
        height, width = image.shape[:2]
        new_size = (width * scale, height * scale)

        # Step 1: Upscale with Lanczos
        upscaled = cv2.resize(image, new_size, interpolation=cv2.INTER_LANCZOS4)

        # Step 2: Apply edge-aware sharpening
        upscaled = self._edge_enhance(upscaled)

        # Step 3: Apply bilateral filter for smooth areas
        upscaled = cv2.bilateralFilter(upscaled, 5, 50, 50)

        # Step 4: Final sharpening pass
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)
        upscaled = cv2.filter2D(upscaled, -1, kernel)

        return np.clip(upscaled, 0, 255).astype(np.uint8)

    def _edge_enhance(self, image: np.ndarray) -> np.ndarray:
        """Enhance edges while preserving smooth areas."""
        # Detect edges
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Dilate edges slightly
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Create edge mask
        edge_mask = edges.astype(np.float32) / 255.0
        edge_mask = np.stack([edge_mask] * 3, axis=-1)

        # Apply unsharp mask more strongly to edge areas
        blurred = cv2.GaussianBlur(image, (0, 0), 2)
        sharpened = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)

        # Blend based on edge mask
        result = image * (1 - edge_mask * 0.5) + sharpened * (edge_mask * 0.5)

        return np.clip(result, 0, 255).astype(np.uint8)

    def upscale_to_4k(self, image: np.ndarray) -> np.ndarray:
        """
        Upscale image to 4K resolution (3840x2160 minimum dimension).
        Automatically calculates required scale factor.
        """
        height, width = image.shape[:2]

        # Calculate scale needed for 4K
        target_width = 3840
        target_height = 2160

        scale_w = target_width / width
        scale_h = target_height / height

        # Use the larger scale to ensure 4K minimum
        scale = max(scale_w, scale_h)

        # Round up to nearest supported scale
        if scale <= 2:
            scale = 2
        elif scale <= 4:
            scale = 4
        else:
            # For very small images, upscale in multiple passes
            return self._multi_pass_upscale(image, target_width, target_height)

        upscaled = self.upscale(image, scale=int(scale), outscale=scale)

        # Resize to exact 4K if needed
        h, w = upscaled.shape[:2]
        if w < target_width or h < target_height:
            # Calculate new dimensions maintaining aspect ratio
            aspect = width / height
            if aspect > target_width / target_height:
                new_width = target_width
                new_height = int(target_width / aspect)
            else:
                new_height = target_height
                new_width = int(target_height * aspect)

            upscaled = cv2.resize(upscaled, (new_width, new_height),
                                  interpolation=cv2.INTER_LANCZOS4)

        return upscaled

    def upscale_to_resolution(self, image: np.ndarray,
                              target_width: int,
                              target_height: int,
                              maintain_aspect: bool = True) -> np.ndarray:
        """
        Upscale image to a specific resolution.

        Args:
            image: Input image
            target_width: Target width in pixels
            target_height: Target height in pixels
            maintain_aspect: If True, maintains aspect ratio (uses larger dimension)

        Returns:
            Upscaled image
        """
        height, width = image.shape[:2]

        if maintain_aspect:
            # Calculate scale to fit target while maintaining aspect
            scale_w = target_width / width
            scale_h = target_height / height
            scale = max(scale_w, scale_h)
        else:
            scale_w = target_width / width
            scale_h = target_height / height
            scale = (scale_w + scale_h) / 2

        # Determine best upscale approach
        if scale <= 1:
            # No upscaling needed, just resize
            return cv2.resize(image, (target_width, target_height),
                              interpolation=cv2.INTER_LANCZOS4)

        # Upscale with AI
        if scale <= 2:
            upscaled = self.upscale(image, scale=2, outscale=scale)
        elif scale <= 4:
            upscaled = self.upscale(image, scale=4, outscale=scale)
        else:
            upscaled = self._multi_pass_upscale(image, target_width, target_height)

        # Final resize to exact dimensions
        if not maintain_aspect:
            upscaled = cv2.resize(upscaled, (target_width, target_height),
                                  interpolation=cv2.INTER_LANCZOS4)

        return upscaled

    def _multi_pass_upscale(self, image: np.ndarray,
                            target_width: int,
                            target_height: int) -> np.ndarray:
        """
        Multi-pass upscaling for very small images that need >4x upscaling.
        """
        current = image.copy()
        height, width = current.shape[:2]

        while width < target_width or height < target_height:
            # Upscale by 4x
            current = self.upscale(current, scale=4)
            height, width = current.shape[:2]

            # Safety check to prevent infinite loop
            if width >= target_width * 2 or height >= target_height * 2:
                break

        # Final resize to target
        return cv2.resize(current, (target_width, target_height),
                          interpolation=cv2.INTER_LANCZOS4)

    @staticmethod
    def get_available_models() -> list:
        """Get list of available upscaling models."""
        return [
            {
                "name": "RealESRGAN_x4plus",
                "scale": 4,
                "description": "General purpose 4x upscaling, best for photos"
            },
            {
                "name": "RealESRGAN_x4plus_anime_6B",
                "scale": 4,
                "description": "Optimized for anime/illustration images"
            },
            {
                "name": "RealESRGAN_x2plus",
                "scale": 2,
                "description": "2x upscaling, faster processing"
            },
            {
                "name": "RealESRNet_x4plus",
                "scale": 4,
                "description": "Alternative 4x model with different characteristics"
            }
        ]

    def is_ai_available(self) -> bool:
        """Check if AI upscaling is available."""
        return self._load_model()

    def get_status(self) -> dict:
        """Get upscaler status information."""
        ai_available = self.is_ai_available()
        return {
            "model_name": self.model_name,
            "ai_available": ai_available,
            "gpu_enabled": self.gpu_id is not None and ai_available,
            "error": self._load_error if not ai_available else None
        }
