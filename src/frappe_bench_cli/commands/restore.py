import os
import json
import shutil
import tarfile
import subprocess
from pathlib import Path
from git import Repo
from rich.console import Console
from rich.progress import Progress

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
    print(f'{backup_path.suffix = }')
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
    
    # Create bench directory
    bench_dir = target_dir / bench_name
    if bench_dir.exists():
        raise ValueError(f"Bench directory already exists: {bench_dir}")
    bench_dir.mkdir(parents=True, exist_ok=True)
    
    # Clone apps
    if not skip_apps:
        apps_dir = bench_dir / 'apps'
        apps_dir.mkdir(parents=True, exist_ok=True)
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Cloning apps...", total=len(bench_info['apps']))
            
            for app in bench_info['apps']:
                try:
                    app_dir = apps_dir / app['name']
                    if not app_dir.exists():
                        repo = Repo.clone_from(app['git_url'], app_dir)
                        repo.git.checkout(app['version'])
                    console.print(f"[green]Successfully cloned {app['name']} at {app['version']}[/green]")
                except Exception as e:
                    console.print(f"[red]Failed to clone {app['name']}: {str(e)}[/red]")
                progress.advance(task)
    
    # Restore sites
    if not skip_sites:
        sites_dir = bench_dir / 'sites'
        sites_dir.mkdir(parents=True, exist_ok=True)
        
        site_backups_dir = backup_dir / 'site_backups'
        if site_backups_dir.exists():
            with Progress() as progress:
                task = progress.add_task("[cyan]Restoring sites...", total=len(bench_info['sites']))
                
                for site in bench_info['sites']:
                    try:
                        site_name = site['name']
                        site_dir = sites_dir / site_name
                        site_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Copy site backup to the site's private/backups directory
                        backup_site_dir = site_backups_dir / site_name
                        if backup_site_dir.exists():
                            private_dir = site_dir / 'private'
                            private_dir.mkdir(parents=True, exist_ok=True)
                            backups_dir = private_dir / 'backups'
                            backups_dir.mkdir(parents=True, exist_ok=True)
                            
                            # Copy the backup file
                            backup_files = list(backup_site_dir.glob('*.sql.gz'))
                            if backup_files:
                                latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
                                shutil.copy2(latest_backup, backups_dir / latest_backup.name)
                                
                                # Run bench restore command
                                result = subprocess.run(
                                    ['bench', 'restore', '--site', site_name, str(latest_backup.name)],
                                    cwd=bench_dir,
                                    capture_output=True,
                                    text=True
                                )
                                
                                if result.returncode == 0:
                                    console.print(f"[green]Successfully restored site {site_name}[/green]")
                                else:
                                    console.print(f"[red]Failed to restore site {site_name}: {result.stderr}[/red]")
                            else:
                                console.print(f"[yellow]No backup files found for site {site_name}[/yellow]")
                        
                    except Exception as e:
                        console.print(f"[red]Failed to restore site {site['name']}: {str(e)}[/red]")
                    progress.advance(task)
    
    return bench_dir
