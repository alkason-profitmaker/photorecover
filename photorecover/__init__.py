"""
PhotoRecover 2.0 - Professional Photo Rescue & AI Restoration
Zero-loss storage recovery, damage repair, filesystem reconstruction, and aspect-ratio preserving AI restoration.
"""

__version__ = "2.0.0"
__author__ = "PhotoRecover Team"

from .enhancer import ImageEnhancer
from .upscaler import AIUpscaler
from .recovery import SDCardRecovery, recover_images, RecoveredItem
from .repair import JPEGRepairer
from .filesystem import FilesystemRecoveryEngine, FAT32Parser, ExFATParser
from .models import ModelRegistry
from .signatures import MultiFormatCarver
from .gui import start_server

__all__ = [
    "ImageEnhancer",
    "AIUpscaler",
    "SDCardRecovery",
    "recover_images",
    "RecoveredItem",
    "JPEGRepairer",
    "FilesystemRecoveryEngine",
    "FAT32Parser",
    "ExFATParser",
    "ModelRegistry",
    "MultiFormatCarver",
    "start_server"
]
