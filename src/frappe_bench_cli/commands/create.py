import os
import json
from pathlib import Path
import subprocess
from typing import Optional
from rich.console import Console
from bench.utils.system import init

class BenchCreator:
    def __init__(self):
        self.console = Console()

    def create_bench_from_info(self, bench_path, info_file, skip_apps=False):
        """Create a bench using configuration from info file"""
        bench_path = Path(bench_path)
        info_file = Path(info_file)
        
        if not info_file.exists():
            raise FileNotFoundError(f"Bench info file not found at {info_file}")
            
        with open(info_file) as f:
            bench_info = json.load(f)
        
        # Create bench directory
        
        # Initialize bench
        if not bench_path.exists():
            bench_path.mkdir(parents=True, exist_ok=True)
            init(f"{bench_path}", python=bench_info.get('python_version', 'python3'), frappe_branch=bench_info.get('frappe_branch', 'version-15'))
        else:
            self.console.print(f"[green]Bench {bench_path} already exist[/green]")
        # Install apps from info
        if not skip_apps:
            for app in bench_info.get('apps', []):
                if app.get('name') == "frappe": continue
                try:
                    self.console.print(f"[cyan]get app {app['name']}...[/cyan]")
                    args = ['bench', 'get-app', app['git_url']]
                    if app.get('version'):
                        args.extend(['--branch',app.get('version')])
                    result = subprocess.run(
                        args,
                        cwd=str(bench_path),
                        capture_output=True,
                        text=True
                    )
                except Exception as e:
                    self.console.print(f"[red]Error get app {app['name']}: {str(e)}[/red]")
        
        # Create sites from info
        for site in bench_info.get('sites', []):
            try:
                site_name = site['name']
                self.console.print(f"[cyan]Creating site {site_name}...[/cyan]")
                result = subprocess.run(
                    ['bench', 'new-site', site_name,'--force'],
                    cwd=str(bench_path),
                    capture_output=True,
                    text=True
                )
            except Exception as e:
                self.console.print(f"[red]Error creating site {site_name}: {str(e)}[/red]")
        
        return bench_path

    def create_bench(self, bench_path, info_file=None, skip_apps=False):
        """
        Create a new Frappe bench
        
        Args:
            bench_path (str): Path where the bench should be created
            info_file (str, optional): Path to bench info JSON file
            skip_apps (bool, optional): Whether to skip installing apps
            
        Returns:
            Path: Path to the created bench
        """
        bench_path = Path(bench_path)
        
        if info_file:
            return self.create_bench_from_info(bench_path, info_file, skip_apps)
        
        # Use standard bench init
        self.console.print(f"[cyan]Creating new bench at {bench_path}...[/cyan]")
        init(bench_path)
        return bench_path
    
def create_bench(bench_path: str, info_file: Optional[str] = None, skip_apps: bool = False, *args,**kwargs) -> Path:
    creator = BenchCreator()
    return creator.create_bench(bench_path, info_file, skip_apps, *args,**kwargs)
