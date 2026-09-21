from pathlib import Path
from shutil import copyfileobj

from fastapi import UploadFile

from app.core.config import get_settings


def save_upload(workspace_id: int, document_id: int, upload: UploadFile) -> tuple[str, int]:
    """Persist an upload in its workspace/document compartment and return its name and size."""
    original_filename = Path(upload.filename or "upload").name
    target_directory = Path(get_settings().upload_storage_path) / str(workspace_id) / str(document_id)
    target_directory.mkdir(parents=True, exist_ok=True)
    target_path = target_directory / original_filename

    with target_path.open("wb") as destination:
        copyfileobj(upload.file, destination)

    return original_filename, target_path.stat().st_size


def get_document_path(workspace_id: int, document_id: int, stored_filename: str) -> Path:
    """Return the expected on-disk path for an uploaded document."""
    return Path(get_settings().upload_storage_path) / str(workspace_id) / str(document_id) / Path(stored_filename).name
