class McServerLibError(Exception):
    """Base exception for mcserverlib."""


class VersionResolutionError(McServerLibError):
    """Raised when a requested version cannot be resolved."""


class DownloadError(McServerLibError):
    """Raised when an artifact download fails."""


class InstallError(McServerLibError):
    """Raised when installation fails."""


class ManifestError(McServerLibError):
    """Raised when server manifest is missing or invalid."""
