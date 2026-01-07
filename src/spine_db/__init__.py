"""SPINE Database - Metadata indexing and browsing for SPINE production runs.

Provides:
- Database schema for tracking production runs
- HDF5 metadata extraction
- CLI indexer for populating database
- Web UI for browsing and filtering runs

Supports SQLite (testing) and PostgreSQL (production).
Works with cloud databases (e.g., Supabase) for multi-site deployments.
"""

from .version import __version__

__all__ = ["__version__"]
