"""
Storage Port Interface (Clean Architecture)
Defines contracts for persisting and retrieving order deliverable files
(CSV batches, Markdown dossiers, Excel workbooks).
"""

from abc import ABC, abstractmethod
from typing import Optional


class StoragePort(ABC):
    """
    Contract for file storage operations, abstracting local filesystem vs.
    Google Cloud Storage (GCS) or AWS S3.
    """

    @abstractmethod
    def upload_file(
        self,
        local_path: str,
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Uploads a local file to storage.
        Returns the canonical storage URI (e.g. gs://bucket/path or file:///path).
        """
        pass

    @abstractmethod
    def generate_download_url(
        self,
        destination_path: str,
        expiration_hours: int = 48
    ) -> str:
        """
        Generates a direct download URL.
        In GCS: V4 Signed URL valid for `expiration_hours`.
        In Local Dev: API relative route (e.g. /api/v1/orders/.../download).
        """
        pass

    @abstractmethod
    def file_exists(self, destination_path: str) -> bool:
        """Checks if a file exists in the storage provider."""
        pass

