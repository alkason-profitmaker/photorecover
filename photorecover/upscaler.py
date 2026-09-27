"""
AI Super-Resolution and Detail Enhancement Module
Uses Real-ESRGAN / RRDBNet with verified weight management and aspect-ratio preserving scaling.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Union, Literal, Tuple
import warnings
from .models import ModelRegistry
from .exceptions import ModelError


class AIUpscaler:
    """
    AI-powered image super-resolution and restoration.
    Maintains strict aspect ratio preservation and offers fallback to Lanczos + bilateral filtering.
    """

    def __init__(self, model_name: str = "RealESRGAN_x4plus", gpu_id: Optional[int] = 0):
        self.model_name = model_name
        self.gpu_id = gpu_id
        self.upsampler = None
        self._model_loaded = False
        self._load_error = None

    def _load_model(self) -> bool:
        """Load the Real-ESRGAN model with checksum verification."""
        if self._model_loaded:
            return True

        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet

            if self.model_name not in ModelRegistry.MODELS:
                self.model_name = "RealESRGAN_x4plus"

            info = ModelRegistry.MODELS[self.model_name]
            netscale = info["scale"]

            if info.get("arch") == "RRDBNet_6B":
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=netscale)
            else:
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=netscale)

            # Ensure model file is safely downloaded & verified
            try:
                model_path = ModelRegistry.ensure_model(self.model_name)
            except Exception as dl_err:
                self._load_error = f"Model download/verification failed: {dl_err}"
                warnings.warn(self._load_error)
                return False

            self.upsampler = RealESRGANer(
                scale=netscale,
                model_path=str(model_path),
                model=model,
                tile=0,
                tile_pad=10,
                pre_pad=0,
                half=False,
                gpu_id=self.gpu_id
            )

            self._model_loaded = True
            return True

        except ImportError as e:
            self._load_error = f"Real-ESRGAN/PyTorch not installed: {e}. Using high-quality algorithmic super-resolution."
            return False

        except Exception as e:
            self._load_error = f"Failed to initialize AI model: {e}. Using algorithmic fallback."
            return False

    def upscale(self, image: np.ndarray, scale: int = 4, outscale: Optional[float] = None) -> np.ndarray:
        """
        Upscale image using AI super-resolution or Lanczos fallback.
        Preserves original aspect ratio.
        """
        if outscale is None:
            outscale = float(scale)

        if self._load_model() and self.upsampler is not None:
            try:
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                output_bgr, _ = self.upsampler.enhance(image_bgr, outscale=outscale)
                return cv2.cvtColor(output_bgr, cv2.COLOR_BGR2RGB)
            except Exception as e:
                warnings.warn(f"AI execution error: {e}. Falling back to Lanczos.")

        return self._fallback_upscale(image, outscale)

    def _fallback_upscale(self, image: np.ndarray, scale: float) -> np.ndarray:
        """
        High-precision algorithmic fallback combining Lanczos-4 with edge preservation.
        Strictly preserves aspect ratio.
        """
        h, w = image.shape[:2]
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))

        # Lanczos-4 interpolation
        upscaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        # Bilateral edge-preserving smoothing to reduce pixelation
        upscaled = cv2.bilateralFilter(upscaled, d=5, sigmaColor=35, sigmaSpace=35)

        # Subtle unsharp edge refinement
        blurred = cv2.GaussianBlur(upscaled, (0, 0), 1.5)
        sharpened = cv2.addWeighted(upscaled, 1.25, blurred, -0.25, 0)

        return np.clip(sharpened, 0, 255).astype(np.uint8)

    def upscale_to_resolution(self,
                              image: np.ndarray,
                              target_width: int,
                              target_height: int,
                              maintain_aspect: bool = True) -> np.ndarray:
        """
        Upscales an image to a target resolution without distortion.
        When maintain_aspect=True, fits image within (target_width, target_height)
        preserving the exact original aspect ratio.
        """
        h, w = image.shape[:2]
        if w == 0 or h == 0:
            return image

        if maintain_aspect:
            # Fit within bounding box
            scale = min(target_width / w, target_height / h)
            final_w = max(1, round(w * scale))
            final_h = max(1, round(h * scale))
        else:
            final_w = target_width
            final_h = target_height
            scale = max(target_width / w, target_height / h)

        if scale <= 1.0:
            # No enlargement needed
            return cv2.resize(image, (final_w, final_h), interpolation=cv2.INTER_LANCZOS4)

        # Apply AI or fallback upscale
        upscaled = self.upscale(image, scale=int(np.ceil(scale)), outscale=scale)

        # Ensure exact pixel dimension matching
        if upscaled.shape[1] != final_w or upscaled.shape[0] != final_h:
            upscaled = cv2.resize(upscaled, (final_w, final_h), interpolation=cv2.INTER_LANCZOS4)

        return upscaled

    def upscale_to_4k(self, image: np.ndarray) -> np.ndarray:
        """
        Upscales image to 4K class resolution (3840x2160 bounding envelope)
        while strictly preserving the photograph's original aspect ratio.
        """
        return self.upscale_to_resolution(image, target_width=3840, target_height=2160, maintain_aspect=True)

    @staticmethod
    def get_available_models() -> list:
        return [
            {"name": k, "scale": v["scale"], "description": v["description"]}
            for k, v in ModelRegistry.MODELS.items()
        ]

    def is_ai_available(self) -> bool:
        return self._load_model()

    def get_status(self) -> dict:
        ai_ok = self.is_ai_available()
        return {
            "model_name": self.model_name,
            "ai_available": ai_ok,
            "gpu_enabled": self.gpu_id is not None and ai_ok,
            "error": self._load_error if not ai_ok else None
        }
