"""
Database configuration and connection management.
"""

import os

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create database directory if it doesn't exist
db_path = settings.database_url.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # For SQLite
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_db():
    """
    Database dependency for FastAPI.
    Yields database session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    # Import all models to ensure they are registered with SQLAlchemy
    from app.models import message, schedule, tenant, user  # noqa

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at: {settings.database_url}")


def reset_db():
    """
    Reset database by dropping and recreating all tables.
    WARNING: This will delete all data!
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("⚠️  Database reset complete - all data deleted!")


# For debugging and manual database operations
def get_db_session():
    """Get a database session for manual operations."""
    return SessionLocal()
