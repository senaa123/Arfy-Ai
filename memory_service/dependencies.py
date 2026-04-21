# memory_service/dependencies.py

from memory_service.db import SessionLocal


def get_db():
    """
    Provide one SQLAlchemy session per request.

    Why this file exists in Phase 4B:
    - route modules should share one dependency source
    - main.py should stay focused on app bootstrap only
    - DB session wiring should not be duplicated across route files
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()