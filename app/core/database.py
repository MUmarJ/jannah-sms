"""
Database configuration and connection management.
Supports both SQLite (local dev) and PostgreSQL (Railway/production).
"""

import os

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings

# Determine database type from URL
is_sqlite = settings.database_url.startswith("sqlite")
is_postgresql = settings.database_url.startswith("postgresql")

# Create database directory for SQLite (local development)
if is_sqlite:
    db_path = settings.database_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

# Configure engine based on database type
if is_sqlite:
    # SQLite configuration (local development)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
        poolclass=NullPool,  # No connection pooling for SQLite
    )
elif is_postgresql:
    # PostgreSQL configuration (Railway production)
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,  # Number of connections to maintain
        max_overflow=10,  # Additional connections if pool is full
        pool_recycle=3600,  # Recycle connections after 1 hour
        poolclass=QueuePool,  # Connection pooling for PostgreSQL
        connect_args={
            "connect_timeout": 10,
            "options": "-c timezone=utc",
        },
    )
else:
    # Fallback for other database types
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=QueuePool,
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
