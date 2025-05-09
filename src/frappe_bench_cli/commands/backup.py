import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from git import Repo
from rich.console import Console
from rich.progress import Progress
from bench.utils.system import run_frappe_cmd


console = Console()

def is_valid_bench(bench_path):
    """Check if the given path is a valid Frappe bench"""
    bench_path = Path(bench_path)
    return (
        bench_path.exists() and
        (bench_path / 'apps').exists() and
        (bench_path / 'sites').exists()
    )

def get_bench_info(bench_path):
    """Extract information about a bench including apps and sites"""
    bench_path = Path(bench_path)
    if not is_valid_bench(bench_path):
        raise ValueError(f"{bench_path} is not a valid Frappe bench")
        
    bench_info = {
        'name': bench_path.name,
        'apps': [],
        'sites': []
    }
    
    # Get apps information
    apps_path = bench_path / 'apps'
    if apps_path.exists():
        for app_dir in apps_path.iterdir():
            if app_dir.is_dir() and (app_dir / '.git').exists():
                try:
                    repo = Repo(app_dir)
                    remote_url = repo.remotes.upstream.url
                    current_branch = repo.active_branch.name
                    bench_info['apps'].append({
                        'name': app_dir.name,
                        'git_url': remote_url,
                        'version': current_branch
                    })
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not get git info for {app_dir.name}: {str(e)}[/yellow]")
    
    # Get sites information
    sites_path = bench_path / 'sites'
    if sites_path.exists():
        for site_dir in sites_path.iterdir():
            if site_dir.is_dir():
                bench_info['sites'].append({
                    'name': site_dir.name
                })
    
    return bench_info

def backup_bench(bench_path, output_dir, compress=True):
    """Backup a single bench"""
    bench_path = Path(bench_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not is_valid_bench(bench_path):
        raise ValueError(f"{bench_path} is not a valid Frappe bench")
        
    bench_info = get_bench_info(bench_path)
    
    # Create backup directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{bench_info['name']}_{timestamp}"
    backup_dir = output_dir / backup_name
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Save bench info
    with open(backup_dir / 'bench_info.json', 'w') as f:
        json.dump(bench_info, f, indent=2)
    
    # Backup sites using bench backup command
    for site in bench_info['sites']:
        try:
            site_name = site['name']
            console.print(f"[cyan]Backing up site {site_name}...[/cyan]")
            run_frappe_cmd("--site", site_name,"backup","--backup-path", backup_dir, bench_path=bench_path)
        except SystemExit as e:
            pass
        except Exception as e:
            console.print(f"[red]Error backing up site {site['name']}: {str(e)}[/red]")
    
    if compress:
        # Create archive
        archive_path = output_dir / f"{backup_name}.tar.gz"
        shutil.make_archive(str(backup_dir), 'gztar', backup_dir)
        shutil.rmtree(backup_dir)
        print(archive_path)
        return archive_path
    
    return backup_dir

def backup_benches(bench_dir, output_dir, bench_name=None, compress=True):
    """
    Backup Frappe benches
    
    Args:
        bench_dir (str): Directory containing Frappe benches
        output_dir (str): Directory to store the backups
        bench_name (str, optional): Name of the specific bench to backup
        compress (bool, optional): Whether to compress the backup
        
    Returns:
        str: Path to the backup directory or archive
    """
    bench_dir = Path(bench_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not bench_dir.exists():
        raise FileNotFoundError(f"Bench directory not found at {bench_dir}")
    
    if bench_name:
        # Backup specific bench
        bench_path = bench_dir / bench_name
        if not is_valid_bench(bench_path):
            raise ValueError(f"{bench_path} is not a valid Frappe bench")
        
        return backup_bench(bench_path, output_dir, compress)
    
    # Backup all benches
    benches = [d for d in bench_dir.iterdir() if d.is_dir() and is_valid_bench(d)]
    
    if not benches:
        console.print("[yellow]No valid Frappe benches found in the benchs directory[/yellow]")
        return None
    
    results = []
    with Progress() as progress:
        task = progress.add_task("[cyan]Backing up benches...", total=len(benches))
        
        for bench_path in benches:
            try:
                result = backup_bench(bench_path, output_dir, compress)
                results.append(result)
                console.print(f"[green]Successfully backed up {bench_path.name} to {result}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to backup {bench_path.name}: {str(e)}[/red]")
            progress.advance(task)
    
    return results
