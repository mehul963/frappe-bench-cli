import os
import json
import shutil
import tarfile
import subprocess
import tempfile
from pathlib import Path
from git import Repo
from rich.console import Console
from rich.progress import Progress
from .create import create_bench
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager

class BenchRestorer:
    def __init__(self, backup_path: str, target_dir: str):
        """
        Initialize BenchRestorer with backup path and target directory
        
        Args:
            backup_path (str): Path to the backup file or directory
            target_dir (str): Directory where to restore the bench
        """
        self.console = Console()
        self.backup_path = Path(backup_path)
        self.target_dir = Path(target_dir)
        
        if not self.backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {self.backup_path}")
        
        self.temp_dir = None
        self.extracted_dir = None
        self.bench_info = None
        self.bench_dir = None
        self.sites_backup_dir = None
        
        # Extract backup and load bench info
        self._extract_backup()
        self.bench_info = self._load_bench_info()

    def _extract_backup(self) -> Path:
        """
        Extract backup to temporary directory
        
        Returns:
            Path: Path to the extracted backup directory
        """
        if self.backup_path.suffix == '.gz':
            self.temp_dir = tempfile.mkdtemp(prefix="frappe_bench_restore_")
            self.console.print(f"[cyan]Extracting backup to temporary directory: {self.temp_dir}[/cyan]")
            
            with tarfile.open(self.backup_path, 'r:gz') as tar:
                tar.extractall(self.temp_dir)
            
            self.extracted_dir = Path(self.temp_dir)
            return self.extracted_dir
        else:
            self.extracted_dir = self.backup_path
            return self.extracted_dir

    def _load_bench_info(self) -> Dict[str, Any]:
        """
        Load bench info from the extracted backup
        
        Returns:
            Dict[str, Any]: Bench information dictionary
        """
        bench_info_path = self.extracted_dir / 'bench_info.json'
        if not bench_info_path.exists():
            raise ValueError(f"Bench info not found in backup: {bench_info_path}")
        
        with open(bench_info_path) as f:
            return json.load(f)

    def restore_site(self, site_name: str) -> bool:
        """
        Restore a single site from backup
        
        Args:
            site_name (str): Name of the site to restore
            
        Returns:
            bool: True if restore was successful, False otherwise
        """
        try:
            site_dir = self.bench_dir / 'sites' / site_name
            site_dir.mkdir(parents=True, exist_ok=True)
            
            # Get site backup from sites_backup directory
            backup_site_dir = self.sites_backup_dir / site_name
            if backup_site_dir.exists():
                # Find the backup file in the site directory
                backup_files = list(backup_site_dir.glob('*.sql.gz'))
                if backup_files:
                    # Since we know there's only one backup file per site
                    backup_file = backup_files[0]
                    self.console.print(f"[cyan]Restoring site {site_name} from {backup_file.name}...[/cyan]")
                    result = subprocess.run(
                        ['bench',"--site",site_name,"restore",backup_file],
                        cwd=self.bench_dir
                    )
                    return result.returncode == 0
                else:
                    self.console.print(f"[yellow]No backup files found for site {site_name}[/yellow]")
            else:
                self.console.print(f"[yellow]No backup directory found for site {site_name}[/yellow]")
            return False
            
        except SystemExit as e:
            self.console.print(f"[red]Failed to restore site {site_name}: Command exited with error[/red]")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            self.console.print(f"[red]Error restoring site {site_name}: {str(e)}[/red]")
            return False

    def restore_bench(self, skip_apps: bool = False, skip_sites: bool = False, 
                     new_name: Optional[str] = None) -> Path:
        """
        Restore Frappe bench from backup
        
        Args:
            skip_apps (bool, optional): Skip installing apps
            skip_sites (bool, optional): Skip restoring sites
            new_name (str, optional): New name for the restored bench
            
        Returns:
            Path: Path to the restored bench directory
        """
        try:
            # Use new name if provided, otherwise use original name
            bench_name = new_name if new_name else self.bench_info['name']
            self.bench_dir = self.target_dir / bench_name
            
            # Create bench using the info file
            self.console.print(f"[cyan]Creating bench at {self.bench_dir}...[/cyan]")
            create_bench(self.bench_dir, self.extracted_dir / 'bench_info.json', skip_apps)
            
            # Restore sites if not skipped
            if not skip_sites:
                self.sites_backup_dir = self.extracted_dir / 'sites_backup'
                if self.sites_backup_dir.exists():
                    for site in self.bench_info['sites']:
                        self.restore_site(site['name'])

            return self.bench_dir
            
        finally:
            # Clean up temporary directory if it was created
            if self.temp_dir and os.path.exists(self.temp_dir):
                self.console.print(f"[cyan]Cleaning up temporary directory: {self.temp_dir}[/cyan]")
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                self.extracted_dir = None

def restore_bench(backup_path: str, target_dir: str, skip_apps: bool = False, 
                 skip_sites: bool = False, new_name: Optional[str] = None, *args, **kwargs) -> Path:
    """
    Convenience function to restore a bench from backup
    
    Args:
        backup_path (str): Path to the backup file or directory
        target_dir (str): Directory where to restore the bench
        skip_apps (bool, optional): Skip installing apps
        skip_sites (bool, optional): Skip restoring sites
        new_name (str, optional): New name for the restored bench
        
    Returns:
        Path: Path to the restored bench directory
    """
    restorer = BenchRestorer(backup_path, target_dir)
    return restorer.restore_bench(skip_apps, skip_sites, new_name, *args, **kwargs)
