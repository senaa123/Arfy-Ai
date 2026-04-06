import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load env from memory_service/.env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# SQLite DB file
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base class for all ORM models
Base = declarative_base()