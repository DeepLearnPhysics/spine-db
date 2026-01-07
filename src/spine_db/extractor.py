"""Metadata extraction from SPINE HDF5 output files.

Reads metadata from HDF5 files and produces canonical Python dicts.
"""

from pathlib import Path
from typing import Dict, Optional

import h5py
import numpy as np


def extract_metadata(file_path: str) -> Dict[str, Optional[str]]:
    """Extract metadata from a SPINE HDF5 output file.

    Parameters
    ----------
    file_path : str
        Path to HDF5 file

    Returns
    -------
    metadata : dict
        Dictionary with keys:
        - file_path: absolute path to file
        - spine_version: SPINE version string
        - spine_prod_version: spine-prod version
        - model_name: model configuration name
        - dataset_name: dataset identifier
        - run: run number (int)
        - subrun: subrun number (int)
        - event_min: minimum event number (int)
        - event_max: maximum event number (int)
        - num_events: total number of events (int)

    Notes
    -----
    Reads metadata from HDF5 root attributes and event data. Falls back to
    inferring from file paths if attributes are not present.
    """
    file_path = str(Path(file_path).resolve())

    metadata = {
        "file_path": file_path,
        "spine_version": None,
        "spine_prod_version": None,
        "model_name": None,
        "dataset_name": None,
        "run": None,
        "subrun": None,
        "event_min": None,
        "event_max": None,
        "num_events": None,
    }

    try:
        with h5py.File(file_path, "r") as f:
            # Try to read from root attributes
            attrs = dict(f.attrs)

            # SPINE version
            if "spine_version" in attrs:
                metadata["spine_version"] = str(attrs["spine_version"])
            elif "version" in attrs:
                metadata["spine_version"] = str(attrs["version"])

            # spine-prod version
            if "spine_prod_version" in attrs:
                metadata["spine_prod_version"] = str(attrs["spine_prod_version"])

            # Model/config name
            if "model_name" in attrs:
                metadata["model_name"] = str(attrs["model_name"])
            elif "config_name" in attrs:
                metadata["model_name"] = str(attrs["config_name"])

            # Dataset name
            if "dataset_name" in attrs:
                metadata["dataset_name"] = str(attrs["dataset_name"])
            elif "dataset" in attrs:
                metadata["dataset_name"] = str(attrs["dataset"])

            # Extract run/subrun/event info from event data
            # SPINE typically stores this in the 'events' dataset
            if "events" in f:
                events_data = f["events"]

                # Try to find run/subrun/event columns
                # Column names vary: 'run', 'run_id', etc.
                if "run" in events_data.dtype.names:
                    runs = events_data["run"][:]
                    metadata["run"] = int(runs[0]) if len(runs) > 0 else None

                if "subrun" in events_data.dtype.names:
                    subruns = events_data["subrun"][:]
                    metadata["subrun"] = int(subruns[0]) if len(subruns) > 0 else None

                if (
                    "event" in events_data.dtype.names
                    or "event_id" in events_data.dtype.names
                ):
                    if "event" in events_data.dtype.names:
                        event_col = "event"
                    else:
                        event_col = "event_id"
                    event_ids = events_data[event_col][:]
                    if len(event_ids) > 0:
                        metadata["event_min"] = int(np.min(event_ids))
                        metadata["event_max"] = int(np.max(event_ids))
                        metadata["num_events"] = len(event_ids)

            # Try to infer model name from file path if not in attributes
            if not metadata["model_name"]:
                path_parts = Path(file_path).parts
                for part in ["icarus", "sbnd", "2x2", "nd-lar", "fsd"]:
                    if part in path_parts:
                        metadata["model_name"] = part
                        break

            # Try to infer dataset name from filename or parent directory
            if not metadata["dataset_name"]:
                filename = Path(file_path).stem
                metadata["dataset_name"] = filename

    except Exception as e:
        print(f"WARNING: Could not read metadata from {file_path}: {e}")

    return metadata


def validate_metadata(metadata: Dict) -> bool:
    """Check if metadata has minimum required fields.

    Parameters
    ----------
    metadata : dict
        Metadata dictionary from extract_metadata

    Returns
    -------
    valid : bool
        True if metadata has at least file_path
    """
    return metadata.get("file_path") is not None


if __name__ == "__main__":
    # Test on a sample file
    import sys

    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        meta = extract_metadata(test_file)
        print("Extracted metadata:")
        for key, value in meta.items():
            print(f"  {key}: {value}")
    else:
        print("Usage: python extractor.py <path_to_hdf5_file>")
