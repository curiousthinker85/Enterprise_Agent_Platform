from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.storage import get_document_path

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx"}
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


class DocumentProcessingError(Exception):
    """The uploaded document could not be extracted into text."""


def extract_text(path: Path) -> str:
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentProcessingError(f"Unsupported file type: {extension or 'no extension'}")
    if not path.is_file():
        raise DocumentProcessingError("Stored upload was not found")

    if extension == ".pdf":
        reader = PdfReader(str(path))
        return "\n\n".join(f"[Page {index}]\n{page.extract_text() or ''}" for index, page in enumerate(reader.pages, start=1))
    if extension == ".docx":
        return "\n".join(paragraph.text for paragraph in DocxDocument(str(path)).paragraphs)
    return path.read_text(encoding="utf-8", errors="replace")


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Create fixed-size overlapping chunks, excluding whitespace-only content."""
    cleaned = text.strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        chunk = cleaned[start : start + chunk_size]
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(cleaned):
            break
        start += chunk_size - overlap
    return chunks


def process_document(db: Session, document: Document) -> int:
    """Extract, chunk, and persist a document. The caller commits status changes."""
    document.status = "processing"
    db.commit()
    db.refresh(document)
    try:
        text = extract_text(get_document_path(document.workspace_id, document.id, document.stored_filename))
        chunks = split_text(text)
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db.add_all(
            DocumentChunk(
                document_id=document.id,
                workspace_id=document.workspace_id,
                chunk_index=index,
                content=content,
                char_count=len(content),
            )
            for index, content in enumerate(chunks)
        )
        document.status = "processed"
        db.commit()
        return len(chunks)
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document.id)
        if document is not None:
            document.status = "failed"
            db.commit()
        if isinstance(exc, DocumentProcessingError):
            raise
        raise DocumentProcessingError(f"Text extraction failed: {exc}") from exc
