import os
import json
from pathlib import Path
from rich.console import Console
from bench.utils.system import run_frappe_cmd,init
from bench.app import App
from bench.bench import Bench

console = Console()

def create_bench_from_info(bench_path, info_file):
    """Create a bench using configuration from info file"""
    bench_path = Path(bench_path)
    info_file = Path(info_file)
    
    if not info_file.exists():
        raise FileNotFoundError(f"Bench info file not found at {info_file}")
        
    with open(info_file) as f:
        bench_info = json.load(f)
    
    # Create bench directory
    bench_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize bench
    init(f"{bench_path}", python=bench_info.get('python_version', 'python3'), frappe_branch=bench_info.get('frappe_branch', 'version-15'))
    
    # Install apps from info
    for app in bench_info.get('apps', []):
        if app.get('name') == "frappe": continue
        try:
            console.print(f"[cyan]Installing app {app['name']}...[/cyan]")
            bench = Bench(bench_path)
            app_obj = App(
                app['git_url'], branch=app.get('branch'), bench=bench
            )
            app_obj.get()
        except Exception as e:
            console.print(f"[red]Error installing app {app['name']}: {str(e)}[/red]")
    
    # Create sites from info
    for site in bench_info.get('sites', []):
        try:
            site_name = site['name']
            console.print(f"[cyan]Creating site {site_name}...[/cyan]")
            run_frappe_cmd("new-site", site_name, bench_path=bench_path)
        except Exception as e:
            console.print(f"[red]Error creating site {site_name}: {str(e)}[/red]")
    
    return bench_path

def create_bench(bench_path, info_file=None):
    """
    Create a new Frappe bench
    
    Args:
        bench_path (str): Path where the bench should be created
        info_file (str, optional): Path to bench info JSON file
        
    Returns:
        Path: Path to the created bench
    """
    bench_path = Path(bench_path)
    
    if info_file:
        return create_bench_from_info(bench_path, info_file)
    
    # Use standard bench init
    console.print(f"[cyan]Creating new bench at {bench_path}...[/cyan]")
    init(bench_path)
    return bench_path 