#!/usr/bin/env python3
"""Indexer helpers - read HDF5 files and insert metadata into database."""
import glob
from pathlib import Path

from .extractor import extract_metadata, validate_metadata
from .schema import SpineFile, create_tables, get_engine, get_session


def index_file(session, file_path: str, skip_existing: bool = True) -> bool:
    """Index a single HDF5 file into the database.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Database session
    file_path : str
        Path to HDF5 file
    skip_existing : bool
        If True, skip files that are already in the database

    Returns
    -------
    success : bool
        True if file was indexed successfully
    """
    file_path = str(Path(file_path).resolve())

    # Check if file already exists
    if skip_existing:
        existing = session.query(SpineFile).filter_by(file_path=file_path).first()
        if existing:
            print(f"SKIP: {file_path} (already in database)")
            return True

    # Extract metadata
    try:
        metadata = extract_metadata(file_path)
        if not validate_metadata(metadata):
            print(f"ERROR: Invalid metadata for {file_path}")
            return False

        # Create database entry
        run = SpineFile(
            file_path=metadata["file_path"],
            spine_version=metadata["spine_version"],
            spine_prod_version=metadata["spine_prod_version"],
            model_name=metadata["model_name"],
            dataset_name=metadata["dataset_name"],
            run=metadata["run"],
            subrun=metadata["subrun"],
            event_min=metadata["event_min"],
            event_max=metadata["event_max"],
            num_events=metadata["num_events"],
        )

        session.add(run)
        session.commit()

        # Build output message
        if metadata["run"] is not None:
            run_info = f"run={metadata['run']}, subrun={metadata['subrun']}"
        else:
            run_info = "run=N/A"

        if metadata["num_events"] is not None:
            event_info = f"events={metadata['num_events']}"
        else:
            event_info = "events=N/A"
        print(
            f"INDEXED: {file_path} "
            f"({run_info}, {event_info}, "
            f"version={metadata['spine_version']})"
        )
        return True

    except Exception as e:
        print(f"ERROR: Failed to index {file_path}: {e}")
        session.rollback()
        return False


def index_files(db_url: str, files: list, skip_existing: bool = True):
    """Index multiple HDF5 files into the database.

    Parameters
    ----------
    db_url : str
        Database connection string
    files : list
        List of file paths or glob patterns
    skip_existing : bool
        If True, skip files that are already in the database
    """
    # Create engine and session
    engine = get_engine(db_url)
    create_tables(engine)
    session = get_session(engine)

    # Expand file list
    file_list = []
    for pattern in files:
        if "*" in pattern or "?" in pattern:
            file_list.extend(glob.glob(pattern))
        else:
            file_list.append(pattern)

    print(f"Found {len(file_list)} file(s) to index")

    # Index each file
    success_count = 0
    error_count = 0

    for file_path in file_list:
        if Path(file_path).exists():
            if index_file(session, file_path, skip_existing):
                success_count += 1
            else:
                error_count += 1
        else:
            print(f"WARNING: File not found: {file_path}")
            error_count += 1

    print(f"\nIndexing complete: {success_count} success, {error_count} errors")

    session.close()
