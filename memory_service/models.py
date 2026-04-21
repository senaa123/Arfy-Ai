from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from memory_service.db import Base

class MemoryRecord(Base):
    """
    Exact/structured memoryy stored in SQLite
    """
    __tablename__ = "memories" #table name in db

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ActionRecord(Base):
    """
     Action log for tracking what the agent did, whether it succeeded, and when.
    """
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(Text, nullable=False)
    type = Column(String(100), nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SummaryRecord(Base):
    """
    Conversation summaries for long-term compression.
    """
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())