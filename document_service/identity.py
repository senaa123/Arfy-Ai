# document_service/identity.py

import hashlib
import uuid
from pathlib import Path


def _normalize_text_for_identity(text: str) -> str:
    """
    Normalize text lightly before building identity hashes.

    We do not want local path differences to affect identity.
    We only want meaningful content + document naming context.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def build_content_hash(text: str) -> str:
    """
    Build a deterministic content hash from extracted document text.

    Why this matters in Phase 4:
    - content hash is portable across machines
    - it helps future cloud sync and conflict checks
    - it avoids using local absolute paths as identity
    """
    normalized = _normalize_text_for_identity(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_source_ref(file_path: str) -> str:
    """
    Build a portable source reference.

    For now this is just the file name.
    It is safe to sync and display, unlike an absolute machine path.
    """
    return Path(file_path).name


def build_portable_document_id(
    *,
    file_name: str,
    extension: str,
    text: str,
) -> str:
    """
    Build a portable document id.

    Phase 4 rule:
    - document identity must not depend on local absolute path
    - identity should remain stable across machines for the same
      named document content snapshot

    We intentionally include:
    - file_name
    - extension
    - content hash

    This makes the id portable, deterministic, and cloud-friendlier.
    """
    content_hash = build_content_hash(text)
    seed = f"arfy:document:{file_name.lower()}:{extension.lower()}:{content_hash}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def build_stable_document_id(file_path: str) -> str:
    """
    Backward-compatible convenience helper for portable document identity.
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    return build_portable_document_id(
        file_name=path.name,
        extension=path.suffix.lower(),
        text=text,
    )


def build_local_snapshot_id(file_path: str) -> str:
    """
    Build a local-only snapshot id.

    This is NOT the shared document identity.
    It is only useful for temp folders, rendered PDF page work dirs, etc.
    """
    path = Path(file_path).resolve()
    stat = path.stat()
    seed = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
