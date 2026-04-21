# memory_service/services/linker.py

from sqlalchemy.orm import Session

from memory_service.models import VectorLinkRecord


def create_vector_link(
    db: Session,
    *,
    owner_type: str,
    owner_public_id: str,
    qdrant_collection: str,
    qdrant_point_id: str,
    vector_kind: str,
    owner_id: int | None = None,
) -> VectorLinkRecord:
    """
    Save one link between a structured owner and a Qdrant point.

    Phase 4:
    - owner_public_id is now the portable lookup key
    - owner_id remains useful for local DB debugging
    """
    link = VectorLinkRecord(
        owner_type=owner_type,
        owner_id=owner_id,
        owner_public_id=owner_public_id,
        qdrant_collection=qdrant_collection,
        qdrant_point_id=qdrant_point_id,
        vector_kind=vector_kind,
    )

    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_vector_link(
    db: Session,
    *,
    owner_type: str,
    owner_public_id: str,
    vector_kind: str,
) -> VectorLinkRecord | None:
    """
    Return the existing link for one structured owner/vector kind pair.

    Phase 4:
    - use the portable owner id instead of relying on a local row id only
    """
    return (
        db.query(VectorLinkRecord)
        .filter(
            VectorLinkRecord.owner_type == owner_type,
            VectorLinkRecord.owner_public_id == owner_public_id,
            VectorLinkRecord.vector_kind == vector_kind,
        )
        .order_by(VectorLinkRecord.id.desc())
        .first()
    )