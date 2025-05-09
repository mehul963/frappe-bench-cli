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

from .commands.backup import backup_bench
from .commands.restore import restore_bench

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """FBM (Frappe Bench Manager) - Backup and restore Frappe benches with ease."""
    pass


@cli.command()
@click.argument('bench_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory for backup files')
@click.option('--no-compress', is_flag=False, help='Do not compress the backup')
def backup(bench_path, output, no_compress):
    """Backup a Frappe bench"""
    try:
        output_dir = output or Path.cwd() / 'backups'
        result = backup_bench(
            bench_path=bench_path,
            output_dir=output_dir,
            compress=not no_compress
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
        console.print(Panel.fit(
            f"[red]Error during backup: {str(e)}[/red]",
            title="Backup Failed"
        ))


@cli.command()
@click.argument('backup_path', type=click.Path(exists=True))
@click.option('--target-dir', '-t', type=click.Path(), help='Target directory for restoration')
@click.option('--skip-apps', is_flag=True, help='Skip installing apps')
@click.option('--skip-sites', is_flag=True, help='Skip restoring sites')
def restore(backup_path, target_dir, skip_apps, skip_sites):
    """Restore Frappe bench from backup"""
    try:
        target_dir = target_dir or Path.cwd()
        result = restore_bench(
            backup_path=backup_path,
            target_dir=target_dir,
            skip_apps=skip_apps,
            skip_sites=skip_sites
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