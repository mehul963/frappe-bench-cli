import os
import json
import shutil
import tarfile
import subprocess
from pathlib import Path
from git import Repo
from rich.console import Console
from rich.progress import Progress
from .create import create_bench
from bench.utils.system import run_frappe_cmd



console = Console()

def extract_backup(backup_path, target_dir):
    """Extract backup archive to target directory"""
    backup_path = Path(backup_path)
    target_dir = Path(target_dir)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    if backup_path.suffix == '.gz':
        with tarfile.open(backup_path, 'r:gz') as tar:
            tar.extractall(target_dir)
        return target_dir
    else:
        raise ValueError(f"Unsupported backup format: {backup_path.suffix}")

def restore_bench(backup_path, target_dir, skip_apps=False, skip_sites=False, new_name=None):
    """
    Restore Frappe bench from backup
    
    Args:
        backup_path (str): Path to the backup file or directory
        target_dir (str): Directory where to restore the bench
        skip_apps (bool, optional): Skip installing apps
        skip_sites (bool, optional): Skip restoring sites
        new_name (str, optional): New name for the restored bench
        
    Returns:
        str: Path to the restored bench directory
    """
    backup_path = Path(backup_path)
    target_dir = Path(target_dir)
    
    # Extract backup if it's an archive
    if backup_path.suffix == '.gz':
        backup_dir = extract_backup(backup_path, target_dir)
    else:
        backup_dir = backup_path
    
    # Load bench info
    bench_info_path = backup_dir / 'bench_info.json'
    if not bench_info_path.exists():
        raise ValueError(f"Bench info not found in backup: {bench_info_path}")
    
    with open(bench_info_path) as f:
        bench_info = json.load(f)
    
    # Use new name if provided, otherwise use original name
    bench_name = new_name if new_name else bench_info['name']
    bench_dir = target_dir / bench_name
    
    # Create bench using the info file
    console.print(f"[cyan]Creating bench at {bench_dir}...[/cyan]")
    create_bench(bench_dir, bench_info_path, skip_apps)
    
    # Restore sites if not skipped
    if not skip_sites:
        sites_backup_dir = backup_dir / 'sites_backup'
        if sites_backup_dir.exists():
            for site in bench_info['sites']:
                try:
                    site_name = site['name']
                    site_dir = bench_dir / 'sites' / site_name
                    site_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Get site backup from sites_backup directory
                    backup_site_dir = sites_backup_dir / site_name
                    if backup_site_dir.exists():
                        # Find the backup file in the site directory
                        backup_files = list(backup_site_dir.glob('*.sql.gz'))
                        if backup_files:
                            # Since we know there's only one backup file per site
                            backup_file = backup_files[0]
                            console.print(f"[cyan]Restoring site {site_name} from {backup_file.name}...[/cyan]")
                            result = subprocess.run(
                                ['bench',"--site",site_name,"restore",backup_file],
                                cwd=bench_dir
                            )
                        else:
                            console.print(f"[yellow]No backup files found for site {site_name}[/yellow]")
                    else:
                        console.print(f"[yellow]No backup directory found for site {site_name}[/yellow]")
                except SystemExit as e:
                    console.print(f"[red]Failed to restore site {site_name}: Command exited with error[/red]")
                    import traceback
                    traceback.print_exc()
                except Exception as e:
                    console.print(f"[red]Error restoring site {site_name}: {str(e)}[/red]")

    return bench_dir
