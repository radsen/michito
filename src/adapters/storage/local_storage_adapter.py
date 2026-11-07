"""
Local Storage Adapter (Clean Architecture)
Persists deliverable files to the local filesystem for offline development and testing.
"""

import os
import shutil
from typing import Optional
from src.application.ports.storage_port import StoragePort


class LocalStorageAdapter(StoragePort):
    """
    Local filesystem implementation of StoragePort.
    Stores files in a local directory (e.g., outputs/).
    """

    def __init__(self, base_dir: Optional[str] = None, base_url: str = ""):
        self.base_dir = os.path.abspath(base_dir or os.path.join(os.getcwd(), "outputs"))
        self.base_url = base_url.rstrip("/")
        os.makedirs(self.base_dir, exist_ok=True)

    def upload_file(
        self,
        local_path: str,
        destination_path: str,
        content_type: Optional[str] = None
    ) -> str:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        target_path = os.path.join(self.base_dir, destination_path.lstrip("/"))
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        if os.path.abspath(local_path) != os.path.abspath(target_path):
            shutil.copy2(local_path, target_path)

        return f"file://{target_path}"

    def generate_download_url(
        self,
        destination_path: str,
        expiration_hours: int = 48
    ) -> str:
        clean_path = destination_path.lstrip("/")
        if self.base_url:
            return f"{self.base_url}/{clean_path}"
        return f"/outputs/{clean_path}"

    def file_exists(self, destination_path: str) -> bool:
        target_path = os.path.join(self.base_dir, destination_path.lstrip("/"))
        return os.path.exists(target_path)

