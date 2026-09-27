"""
PhotoRecover - Exception Taxonomy
Defines structured exceptions for recovery, parsing, repair, and AI model management.
"""

class PhotoRecoverError(Exception):
    """Base exception for all PhotoRecover errors."""
    pass


class SourceMediaError(PhotoRecoverError):
    """Raised when there is an issue reading source media or device."""
    def __init__(self, message: str, offset: int = 0, is_bad_sector: bool = False):
        super().__init__(message)
        self.offset = offset
        self.is_bad_sector = is_bad_sector


class DeviceAccessError(SourceMediaError):
    """Raised when insufficient permissions prevent opening raw devices."""
    pass


class BadSectorError(SourceMediaError):
    """Raised when an unreadable bad sector is encountered."""
    pass


class FormatCarveError(PhotoRecoverError):
    """Raised when carving encounters an unrecoverable format corruption."""
    pass


class CorruptStreamError(PhotoRecoverError):
    """Raised when an entropy or image stream is truncated or malformed."""
    pass


class FilesystemError(PhotoRecoverError):
    """Base error for filesystem structure parsing (FAT32, exFAT)."""
    pass


class PartitionTableError(FilesystemError):
    """Raised when partition table (MBR/GPT) is invalid or unreadable."""
    pass


class ModelError(PhotoRecoverError):
    """Base error for AI model handling."""
    pass


class ModelIntegrityError(ModelError):
    """Raised when downloaded model weights fail SHA-256 verification."""
    pass


class ModelDownloadError(ModelError):
    """Raised when model weights cannot be downloaded or server is unreachable."""
    pass
