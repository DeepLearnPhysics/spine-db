#!/usr/bin/env python3
"""Command-line entry points for spine-db."""

import argparse
from pathlib import Path
from typing import List, Optional

from . import app as app_module
from . import indexer
from . import setup as setup_module


def _load_files_list(path: str) -> List[str]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def _add_inject_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "inject",
        help="Index SPINE HDF5 output files into the metadata database",
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Database connection string (e.g., sqlite:///spine_files.db)",
    )
    file_group = parser.add_mutually_exclusive_group(required=True)
    file_group.add_argument(
        "--source",
        "-s",
        nargs="+",
        help="HDF5 files to index (supports globs)",
    )
    file_group.add_argument(
        "--source-list",
        "-S",
        help="Text file containing list of HDF5 files (one per line)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-index files that are already in the database",
    )


def _add_app_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "app",
        help="Launch the SPINE runs browser web interface",
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Database connection string (e.g., sqlite:///spine_files.db)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to bind to (default: 8050)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode with auto-reload",
    )


def _add_setup_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "setup",
        help="Initialize the SPINE database schema",
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Database connection string (e.g., sqlite:///spine_files.db)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spine-db",
        description=("Utilities for indexing and browsing SPINE production runs"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_inject_subcommand(subparsers)
    _add_app_subcommand(subparsers)
    _add_setup_subcommand(subparsers)
    return parser


def _run_inject(
    db_url: str,
    sources: Optional[List[str]],
    source_list: Optional[str],
    skip_existing: bool,
) -> int:
    if source_list:
        sources = _load_files_list(source_list)
    if not sources:
        raise ValueError("No files provided for indexing.")
    indexer.index_files(db_url, sources, skip_existing=skip_existing)
    return 0


def _run_app(db_url: str, host: str, port: int, debug: bool) -> int:
    dash_app = app_module.create_app(db_url)
    print("\nStarting SPINE Runs Browser...")
    print(f"Database: {db_url}")
    print(f"Open your browser to: http://{host}:{port}/\n")
    dash_app.run(host=host, port=port, debug=debug)
    return 0


def _run_setup(db_url: str) -> int:
    setup_module.setup_schema(["--db", db_url])
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "inject":
        return _run_inject(
            args.db,
            args.source,
            args.source_list,
            skip_existing=not args.no_skip_existing,
        )
    if args.command == "app":
        return _run_app(args.db, args.host, args.port, args.debug)
    if args.command == "setup":
        return _run_setup(args.db)

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
