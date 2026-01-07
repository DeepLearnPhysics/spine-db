# SPINE Database (spine-db)

Standalone metadata indexing and browsing system for SPINE production runs.

**Key Feature**: Works with cloud databases (e.g., Supabase) for **multi-site deployments** - index files from S3DF, NERSC, or anywhere, all writing to one central database.

## Quick Start

### 1. Install

```bash
# From this repo root
pip install -e .

# Or from PyPI (once published)
# pip install spine-db
```

### 2. Set Up Database

**Option A: Cloud Database (Recommended for Multi-Site)**

For production at multiple sites (S3DF, NERSC, etc.):

```bash
# Sign up at supabase.com (free, no credit card)
# Create project → get connection string
DB_URL="postgresql://user:pass@db.xyz.supabase.co:5432/postgres"

# Works from anywhere - S3DF, NERSC, your laptop
```

**Option B: Local Testing with SQLite**

```bash
# Database created automatically on first use
DB_URL="sqlite:///spine_files.db"
```

**Option C: Local PostgreSQL at S3DF/NERSC**

```bash
# Install postgres
conda install postgresql
initdb ~/postgres_data
pg_ctl -D ~/postgres_data start

# Create database
createdb spine_db
DB_URL="postgresql:///spine_db"
```

Initialize the schema once:

```bash
spine-db setup --db $DB_URL
```

### 3. Index Your Files

```bash
# Index from glob pattern
spine-db inject --db $DB_URL --source /path/to/output/*.h5

# Index from file list
spine-db inject --db $DB_URL --source-list file_list.txt

# Re-index existing files
spine-db inject --db $DB_URL --source output/*.h5 --no-skip-existing
```

### 4. Launch Web UI

```bash
spine-db app --db $DB_URL --port 8050
```

Open your browser to http://localhost:8050

## Features

**Current**:

- **Database Schema**: `spine_files` table tracking file_path, spine_version, model_name, dataset_name, created_at
- **Multi-Site Support**: Works with cloud databases - S3DF and NERSC can write to same DB
- **Metadata Extractor**: Reads HDF5 root attributes, infers from file paths
- **Indexer**: CLI tool with glob patterns, file lists, skip/re-index options
- **Web UI**: 
  - Filter by version, model, dataset
  - Sort by creation date (newest first)
  - Adjustable result limit
  - Full file path tooltips
  - Total and filtered counts

**Future Enhancements**:

- Server-side pagination for large result sets
- Semantic version parsing (major.minor.patch) for better filtering
- Advanced analytics and histograms
- Export filtered results to CSV/file lists
- REST API for programmatic access
- Detailed metadata panel on row click

## Architecture

```
src/spine_db/
├── __init__.py       # Package metadata
├── cli.py            # CLI entry point
├── schema.py         # SQLAlchemy models
├── extractor.py      # HDF5 metadata extraction
├── indexer.py        # Indexer logic
├── setup.py          # Database setup helper
├── app.py            # Dash web UI
└── README.md         # This file
```

## Usage Examples

### Testing Locally

```bash
# Index some files
spine-db inject \
    --db sqlite:///test_spine_files.db \
    --source jobs/*/output/*.h5

# Launch UI
spine-db app \
    --db sqlite:///test_spine_files.db \
    --debug
```

### Production Setup

**Multi-Site with Cloud Database** (S3DF + NERSC → Supabase):

```bash
# 1. Create free Supabase project at supabase.com
#    Get connection string from project settings

# 2. Index from S3DF
ssh s3df.slac.stanford.edu
spine-db inject \
    --db postgresql://user:pass@db.xyz.supabase.co:5432/postgres \
    --source-list /sdf/data/neutrino/spine_outputs.txt

# 3. Index from NERSC (same database!)
ssh perlmutter-p1.nersc.gov
spine-db inject \
    --db postgresql://user:pass@db.xyz.supabase.co:5432/postgres \
    --source /global/cfs/cdirs/dune/www/data/*.h5

# 4. Run UI anywhere (or deploy to Render/Railway for free)
spine-db app \
    --db postgresql://user:pass@db.xyz.supabase.co:5432/postgres \
    --host 0.0.0.0 \
    --port 8050
```

**Local PostgreSQL at S3DF**:

```bash
# 1. Set up PostgreSQL
conda install postgresql
initdb ~/postgres_data
pg_ctl -D ~/postgres_data start
createdb spine_db

# 2. Index production outputs
spine-db inject \
    --db postgresql:///spine_db \
    --source-list /path/to/production_files.txt

# 3. Run UI (access via SSH tunnel)
spine-db app \
    --db postgresql:///spine_db \
    --host 0.0.0.0 \
    --port 8050

# From your laptop:
# ssh -L 8050:localhost:8050 user@s3df.slac.stanford.edu
# Then open http://localhost:8050
```

### Extracting Metadata

```bash
# Test metadata extraction on a file
python -m spine_db.extractor /path/to/output.h5
```

## Database Schema

```sql
CREATE TABLE spine_files (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR UNIQUE NOT NULL,
    spine_version VARCHAR,
    spine_prod_version VARCHAR,
    model_name VARCHAR,
    dataset_name VARCHAR,
    run INTEGER,
    subrun INTEGER,
    event_min INTEGER,
    event_max INTEGER,
    num_events INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_spine_files_file_path ON spine_files(file_path);
CREATE INDEX idx_spine_files_created_at ON spine_files(created_at);
CREATE INDEX idx_spine_files_model_name ON spine_files(model_name);
CREATE INDEX idx_spine_files_dataset_name ON spine_files(dataset_name);
CREATE INDEX idx_spine_files_run ON spine_files(run);
CREATE INDEX idx_spine_files_subrun ON spine_files(subrun);
```

## Database Size Estimates

Each row stores ~350 bytes (file path, version, model, dataset, timestamps, indexes).

**Examples**:
- 1,000 files = ~350 KB
- 10,000 files = ~3.5 MB  
- 100,000 files = ~35 MB
- 1,000,000 files = ~350 MB

**Supabase free tier (500 MB)** = ~1.4 million files = several years of heavy production.

## Integration with spine-prod

### Automatic Indexing After Job Completion

Add indexing to your submit.py workflow:

```python
# After job completion
if not dry_run and job_ids:
    # Index output files
    output_files = glob.glob(f"{job_dir}/output/*.h5")
    if output_files:
        subprocess.run([
            "spine-db", "inject",
            "--db", os.environ.get("SPINE_DB_URL", "sqlite:///spine_files.db"),
            "--source", *output_files
        ])
```

### Future: Pipeline Integration

In pipelines, add an indexing stage:

```yaml
stages:
  - name: reconstruction
    config: infer/icarus/latest.cfg
    files: data/*.root
    
  - name: index
    depends_on: [reconstruction]
    # Custom indexer stage
    script: |
      spine-db inject \
        --db $SPINE_DB_URL \
        --source {{ reconstruction.output }}
```

## Contributing

This is Phase 1 - a minimal working system. Future phases will:
1. Add robust pagination and versioning (Phase 2)
2. Implement security and deployment (Phase 3)
3. Extract to separate repo with migrations (Phase 4)
4. Add advanced features (Phase 5)

Feedback and contributions welcome!

## License

Same as SPINE and spine-prod.
