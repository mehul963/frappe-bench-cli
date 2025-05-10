#!/usr/bin/env python3
"""
FBM (Frappe Bench Manager) - A tool to backup and restore Frappe benches
"""

import os
import sys
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from .commands.backup import backup_bench, backup_all_benches
from .commands.restore import restore_bench
from .commands.create import create_bench

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """FBM (Frappe Bench Manager) - Backup and restore Frappe benches with ease."""
    pass


@cli.group()
def backup():
    """Backup Frappe benches"""
    pass


@backup.command()
@click.argument('bench_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory for backup files')
@click.option('--no-compress', is_flag=True, help='Do not compress the backup')
@click.option('--backup-folder', '-b', type=click.Path(), help='Backup folder')
@click.option('--exclude-files', is_flag=True, help='Exclude files from backup')
def single(bench_path, output, no_compress, backup_folder, exclude_files):
    """Backup a single Frappe bench"""
    try:
        output_dir = output or Path.cwd() / 'backups'
        result = backup_bench(
            bench_path=Path(bench_path),
            output_dir=output_dir,
            compress=not no_compress,
            backup_folder=backup_folder,
            exclude_files=exclude_files
        )
        
        if result:
            console.print(Panel.fit(
                f"[green]Successfully backed up bench to {result}[/green]",
                title="Backup Complete"
            ))
        else:
            console.print(Panel.fit(
                "[yellow]Backup failed[/yellow]",
                title="Backup Failed"
            ))
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        console.print(Panel.fit(
            f"[red]Error during backup: {str(e)}[/red]",
            title="Backup Failed"
        ))


@backup.command()
@click.argument('benches_folder', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory for backup files')
@click.option('--no-compress', is_flag=True, help='Do not compress the backup')
@click.option('--backup-folder', '-b', type=click.Path(), help='Backup folder')
@click.option('--exclude-files', is_flag=True, help='Exclude files from backup')
def all(benches_folder, output, no_compress, backup_folder, exclude_files):
    """Backup all Frappe benches in a folder"""
    try:
        output_dir = output or Path.cwd() / 'backups'
        results = backup_all_benches(
            benches_folder=benches_folder,
            output_dir=output_dir,
            compress=not no_compress,
            backup_folder=backup_folder,
            exclude_files=exclude_files
        )
        
        if results:
            console.print(Panel.fit(
                f"[green]Successfully backed up {len(results)} benches:[/green]\n" + 
                "\n".join(f"- {result}" for result in results),
                title="Backup Complete"
            ))
        else:
            console.print(Panel.fit(
                "[yellow]No benches were backed up[/yellow]",
                title="Backup Failed"
            ))
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        console.print(Panel.fit(
            f"[red]Error during backup: {str(e)}[/red]",
            title="Backup Failed"
        ))


@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
@click.option('--target-dir', '-t', type=click.Path(), help='Target directory for restoration')
@click.option('--skip-apps', is_flag=True, help='Skip installing apps')
@click.option('--skip-sites', is_flag=True, help='Skip restoring sites')
@click.option('--new-name', '-n', help='New name for the restored bench')
def restore(backup_path, target_dir, skip_apps, skip_sites, new_name):
    """Restore Frappe bench from backup"""
    try:
        target_dir = target_dir or Path.cwd()
        result = restore_bench(
            backup_path=backup_path,
            target_dir=target_dir,
            skip_apps=skip_apps,
            skip_sites=skip_sites,
            new_name=new_name
        )
        
        console.print(Panel.fit(
            f"[green]Successfully restored bench to {result}[/green]",
            title="Restore Complete"
        ))
        
    except Exception as e:
        console.print(Panel.fit(
            f"[red]Error during restore: {str(e)}[/red]",
            title="Restore Failed"
        ))


@cli.command()
@click.argument('bench_path', type=click.Path())
@click.option('--info-file', '-i', type=click.Path(exists=True), help='Path to bench info JSON file')
def create(bench_path, info_file):
    """Create a new Frappe bench"""
    try:
        result = create_bench(
            bench_path=bench_path,
            info_file=info_file
        )
        
        console.print(Panel.fit(
            f"[green]Successfully created bench at {result}[/green]",
            title="Create Complete"
        ))
        
    except Exception as e:
        console.print(Panel.fit(
            f"[red]Error during bench creation: {str(e)}[/red]",
            title="Create Failed"
        ))