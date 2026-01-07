"""Database schema for SPINE production runs."""

import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Engine, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Load environment variables from spine_db/.env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

Base = declarative_base()


class SpineFile(Base):
    """Represents a single SPINE output file.

    Attributes
    ----------
    id : int
        Primary key
    file_path : str
        Absolute path to the HDF5 output file
    spine_version : str
        SPINE version string (e.g., "0.7.0")
    spine_prod_version : str
        spine-prod version used for job submission
    model_name : str
        Name of the model/config used (e.g., "icarus_full_chain_co_250625")
    dataset_name : str
        Dataset identifier (e.g., "icarus_run2_data")
    run : int
        Run number (fixed per file)
    subrun : int
        Subrun number (fixed per file)
    event_min : int
        Minimum event number in file
    event_max : int
        Maximum event number in file
    num_events : int
        Total number of events in file
    created_at : datetime
        Timestamp when this record was created
    """

    __tablename__ = "spine_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, nullable=False, unique=True, index=True)
    spine_version = Column(String, nullable=True)
    spine_prod_version = Column(String, nullable=True)
    model_name = Column(String, nullable=True, index=True)
    dataset_name = Column(String, nullable=True, index=True)
    run = Column(Integer, nullable=True, index=True)
    subrun = Column(Integer, nullable=True, index=True)
    event_min = Column(Integer, nullable=True)
    event_max = Column(Integer, nullable=True)
    num_events = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        if self.run is not None:
            run_info = f"run={self.run}, subrun={self.subrun}"
        else:
            run_info = "run=N/A"
        return (
            f"<SpineFile(id={self.id}, "
            f"{run_info}, "
            f"events={self.num_events}, "
            f"version={self.spine_version})>"
        )


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Create SQLAlchemy engine.

    Parameters
    ----------
    db_url : str, optional
        Database connection string (e.g.,
        "postgresql://user:pass@localhost/spine_db" or
        "sqlite:///spine_files.db" for local testing).
        If None, reads from DATABASE_URL environment variable.

    Returns
    -------
    engine : sqlalchemy.Engine
        SQLAlchemy engine

    Raises
    ------
    ValueError
        If db_url is None and DATABASE_URL environment variable is not set
    """
    if db_url is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url is None:
            raise ValueError(
                "No database URL provided. Either pass db_url parameter "
                "or set DATABASE_URL environment variable."
            )

    # Configure connection args based on database type
    connect_args = {}
    if db_url.startswith("postgresql"):
        connect_args = {"sslmode": "require"}

    return create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        poolclass=NullPool,
    )


def create_tables(engine: Engine):
    """Create all tables in the database.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        SQLAlchemy engine
    """
    Base.metadata.create_all(engine)


def get_session(engine: Engine) -> Session:
    """Create a database session.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        SQLAlchemy engine

    Returns
    -------
    session : sqlalchemy.orm.Session
        Database session
    """
    return sessionmaker(bind=engine)()
