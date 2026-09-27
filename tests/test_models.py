"""
Unit Test: AI Model Registry and Checksums
"""

from pathlib import Path
import hashlib
from photorecover.models import ModelRegistry


def test_model_registry_configurations():
    """Verify registered models have valid configurations and SHA-256 targets."""
    assert "RealESRGAN_x4plus" in ModelRegistry.MODELS
    info = ModelRegistry.MODELS["RealESRGAN_x4plus"]
    assert info["scale"] == 4
    assert len(info["sha256"]) == 64
    assert info["url"].startswith("https://")


def test_verify_file_checksum(tmp_path):
    """Test SHA-256 verification against corrupt and valid local files."""
    dummy_model = tmp_path / "test_model.pth"
    dummy_bytes = b"pre_trained_weights_binary_payload"
    dummy_model.write_bytes(dummy_bytes)

    valid_hash = hashlib.sha256(dummy_bytes).hexdigest()
    assert ModelRegistry.verify_file(dummy_model, valid_hash) is True
    assert ModelRegistry.verify_file(dummy_model, "0000000000000000000000000000000000000000000000000000000000000000") is False
