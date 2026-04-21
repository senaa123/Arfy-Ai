# memory_service/models.py

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from memory_service.db import Base


class MemoryRecord(Base):
    """
    Durable structured memory.

    This is where exact facts/preferences/known metadata live.
    Examples:
    - favorite_app = Spotify
    - preferred_response_style = detailed
    - usual_location = Colombo

    Phase 4:
    - memory_id is the portable public id
    - id remains the local DB row id
    """

    __tablename__ = "memory_records"

    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    category = Column(String(100), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)

    session_id = Column(String(100), nullable=True, index=True)
    document_id = Column(String(100), nullable=True, index=True)

    source = Column(String(50), nullable=False, default="agent")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ActionRecord(Base):
    """
    Structured action log.

    Phase 4:
    - action_id is the portable public id
    - id remains the local DB row id
    """

    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    session_id = Column(String(100), nullable=True, index=True)
    action = Column(Text, nullable=False)
    type = Column(String(100), nullable=False, index=True)
    payload_json = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class SessionRecord(Base):
    """
    Structured metadata for a finished or active session.

    session_id already acts as the public/stable session identifier,
    so we keep that as the portable session key.
    """

    __tablename__ = "session_records"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(100), nullable=False, unique=True, index=True)

    started_at = Column(String(100), nullable=True)
    ended_at = Column(String(100), nullable=True)

    summary = Column(Text, nullable=True)
    message_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class DocumentRecord(Base):
    """
    Structured document metadata.

    Phase 4:
    - document_id is the portable shared document id
    - source_ref is sync-safe display/reference metadata
    - local_file_path is local-only metadata
    - content_hash helps future sync / dedupe / verification
    """

    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(String(100), nullable=False, unique=True, index=True)

    file_name = Column(String(255), nullable=False)
    source_ref = Column(String(255), nullable=False, index=True)
    local_file_path = Column(Text, nullable=True)
    extension = Column(String(20), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)

    text_length = Column(Integer, nullable=False, default=0)
    chunk_count = Column(Integer, nullable=False, default=0)
    ocr_used = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class DocumentChunkRecord(Base):
    """
    Structured document chunk row.

    chunk_id is already the stable public chunk identity.
    """

    __tablename__ = "document_chunk_records"

    id = Column(Integer, primary_key=True, index=True)

    chunk_id = Column(String(100), nullable=False, unique=True, index=True)
    document_id = Column(String(100), nullable=False, index=True)

    chunk_index = Column(Integer, nullable=False, index=True)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)

    text = Column(Text, nullable=False)
    indexed_to_vector = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class VectorLinkRecord(Base):
    """
    Link table connecting structured rows to Qdrant points.

    Phase 4:
    - owner_id remains the local SQL row id
    - owner_public_id becomes the portable owner identifier
    - vector_link_id becomes the portable link identifier
    """

    __tablename__ = "vector_links"

    id = Column(Integer, primary_key=True, index=True)
    vector_link_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    owner_type = Column(String(50), nullable=False, index=True)

    # Local DB row id for debugging / local joins
    owner_id = Column(Integer, nullable=True, index=True)

    # Portable owner identifier used by future sync/migration logic
    owner_public_id = Column(String(100), nullable=False, index=True)

    qdrant_collection = Column(String(100), nullable=False, index=True)
    qdrant_point_id = Column(String(100), nullable=False, unique=True, index=True)
    vector_kind = Column(String(100), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())