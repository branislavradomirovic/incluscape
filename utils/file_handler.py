import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional


class FileHandler:
    """Safe file storage helpers for uploaded documents."""

    def __init__(self, upload_folder: str = "./uploads"):
        self.upload_folder = Path(upload_folder)
        self.upload_folder.mkdir(parents=True, exist_ok=True)

    def save(self, source_path: str, subfolder: str = "") -> str:
        """Copy a file into the upload folder and return the stored path."""
        dest_dir = self.upload_folder / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_name = Path(source_path).name
        dest_path = dest_dir / file_name
        # Avoid path traversal
        dest_path = dest_path.resolve()
        if not str(dest_path).startswith(str(self.upload_folder.resolve())):
            raise ValueError("Invalid file path.")
        shutil.copy2(source_path, dest_path)
        return str(dest_path)

    def save_bytes(self, data: bytes, file_name: str, subfolder: str = "") -> str:
        """Save raw bytes as a file and return the stored path."""
        # Sanitise file name
        safe_name = Path(file_name).name
        dest_dir = self.upload_folder / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = (dest_dir / safe_name).resolve()
        if not str(dest_path).startswith(str(self.upload_folder.resolve())):
            raise ValueError("Invalid file path.")
        dest_path.write_bytes(data)
        return str(dest_path)

    @staticmethod
    def hash_file(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def allowed_extension(file_name: str, allowed: list[str]) -> bool:
        ext = Path(file_name).suffix.lstrip(".").lower()
        return ext in [a.lower() for a in allowed]
