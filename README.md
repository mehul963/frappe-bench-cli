# FBM (Frappe Bench Manager)

A command-line tool for backing up and restoring Frappe benches.

## Features

- Backup Frappe benches with their configuration and sites
- Restore benches from backups
- Support for both CLI and programmatic usage
- Rich progress tracking and error reporting

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/fbm.git
cd fbm

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### From PyPI (Coming Soon)

```bash
pip install fbm
```

## Usage

### CLI Interface

```bash
# Backup a bench
fbm backup /path/to/bench --output /path/to/backups

# Backup without compression
fbm backup /path/to/bench --no-compress

# Restore a bench
fbm restore /path/to/backup.tar.gz --target-dir /path/to/restore

# Restore with options
fbm restore /path/to/backup.tar.gz --skip-apps --skip-sites
```

### Programmatic Usage

```python
from frappe_bench_cli import backup, restore

# Backup a bench
result = backup(
    bench_path="/path/to/bench",
    output_dir="/path/to/backups",
    compress=True  # optional
)

# Restore a bench
result = restore(
    backup_path="/path/to/backup.tar.gz",
    target_dir="/path/to/restore",
    skip_apps=False,  # optional
    skip_sites=False  # optional
)
```

## Project Structure

```
fbm/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── src/
    └── frappe_bench_cli/
        ├── __init__.py
        ├── main.py          # CLI entrypoint and programmatic API
        ├── cli.py           # CLI command definitions
        └── commands/        # Core functionality
            ├── __init__.py
            ├── backup.py
            └── restore.py
```

## Backup Format

The backup includes:
- Bench configuration (apps, sites)
- Site backups
- Git information for apps

The backup is stored as a `.tar.gz` archive containing:
- `bench_info.json`: Bench configuration
- `site_backups/`: Directory containing site backups

## License

MIT
