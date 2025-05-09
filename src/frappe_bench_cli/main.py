#!/usr/bin/env python3
"""
FBM (Frappe Bench Manager) - Main module for programmatic usage and CLI entrypoint
"""
from .cli import cli
from .commands.backup import backup_bench
from .commands.restore import restore_bench
from .commands.create import create_bench

# Programmatic API

def backup(bench_path, output_dir, compress=True):
    """
    Backup a Frappe bench programmatically
    
    Args:
        bench_path (str): Path to the Frappe bench to backup
        output_dir (str): Directory to store the backup
        compress (bool, optional): Whether to compress the backup
        
    Returns:
        str: Path to the backup directory or archive
    """
    return backup_bench(
        bench_path=bench_path,
        output_dir=output_dir,
        compress=compress
    )


def restore(backup_path, target_dir, skip_apps=False, skip_sites=False, new_name=None):
    """
    Restore Frappe bench programmatically
    
    Args:
        backup_path (str): Path to the backup file or directory
        target_dir (str): Directory where to restore the bench
        skip_apps (bool, optional): Skip installing apps
        skip_sites (bool, optional): Skip restoring sites
        new_name (str, optional): New name for the restored bench
        
    Returns:
        str: Path to the restored bench directory
    """
    return restore_bench(
        backup_path=backup_path,
        target_dir=target_dir,
        skip_apps=skip_apps,
        skip_sites=skip_sites,
        new_name=new_name
    )

def create(bench_path, info_file=None):
    """
    Create a new Frappe bench programmatically
    
    Args:
        bench_path (str): Path where the bench should be created
        info_file (str, optional): Path to bench info JSON file
        
    Returns:
        str: Path to the created bench
    """
    return create_bench(
        bench_path=bench_path,
        info_file=info_file
    )

# CLI entrypoint
if __name__ == '__main__':
    cli()