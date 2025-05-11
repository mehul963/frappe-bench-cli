import os
import json
import shutil
import subprocess
from pathlib import Path
from rich.console import Console
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from git import Repo


class BenchBackupManager:
    def __init__(
        self,
        bench_dir: Union[str, Path],
        output_dir: Union[str, Path],
        compress: bool = True,
        exclude_files: bool = False,
        backup_folder: Optional[str] = None
    ):
        self.bench_dir = Path(bench_dir)
        self.output_dir = Path(output_dir)
        self.compress = compress
        self.exclude_files = exclude_files
        self.backup_folder = Path(backup_folder) if backup_folder else None
        self.console = Console()

        if not self.bench_dir.exists():
            raise FileNotFoundError(f"Bench directory not found: {self.bench_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def sites(self, bench_path: Path) -> List[str]:
        return [
            path
            for path in os.listdir(os.path.join(bench_path, "sites"))
            if os.path.exists(os.path.join(bench_path, "sites", path, "site_config.json"))
        ]
        
    @property
    def benches(self) -> List[Path]:
        return [
            path
            for path in self.bench_dir.iterdir()
            if self.is_valid_bench(path)
        ]
    
    @staticmethod
    def is_valid_bench(bench_path: Path) -> bool:
        """Check if the given path is a valid Frappe bench."""
        return (
            bench_path.exists() and
            (bench_path / 'apps').exists() and
            (bench_path / 'sites').exists()
        )
        
    @staticmethod
    def get_python_version_from_bench(bench_path):
        python_executable = os.path.join(bench_path, 'env', 'bin', 'python')

        if not os.path.isfile(python_executable):
            return None

        try:
            result = subprocess.run(
                [python_executable, '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            version_output = result.stdout.strip() or result.stderr.strip()  # Sometimes it's in stderr
            _, version = version_output.split()
            major, minor, *_ = version.split(".")
            return f"python{major}.{minor}"
        except Exception as e:
            return None 
        
    def get_bench_info(self, bench_path: Path) -> Dict[str, Any]:
        """Extract information about a bench including apps and sites."""
        if not self.is_valid_bench(bench_path):
            raise ValueError(f"{bench_path} is not a valid Frappe bench")

        info: Dict[str, Any] = {'python': self.get_python_version_from_bench(bench_path),'name': bench_path.name, 'apps': [], 'sites': []}

        for app_dir in (bench_path / 'apps').iterdir():
            if app_dir.is_dir() and (app_dir / '.git').exists():
                try:
                    repo = Repo(app_dir)
                    remote_url = repo.remotes.upstream.url
                    branch = repo.active_branch.name
                    info['apps'].append({'name': app_dir.name, 'git_url': remote_url, 'version': branch})
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not get git info for {app_dir.name}: {e}[/yellow]")

        info['sites'] = [
            {
                'name': site
            }
            for site in self.sites(bench_path)
        ]

        return info

    def backup_single_bench(self, bench_path: Path) -> Path:
        """Backup a single bench to the output directory."""
        bench_info = self.get_bench_info(bench_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{bench_info['name']}_{timestamp}"
        
        # Use specified backup folder if provided, otherwise use default output_dir
        backup_dir = Path(self.backup_folder) / backup_name if self.backup_folder else self.output_dir / backup_name
        sites_backup_dir = backup_dir / 'sites_backup'
        backup_dir.mkdir(parents=True)
        sites_backup_dir.mkdir(parents=True)

        # Save bench metadata
        with open(backup_dir / 'bench_info.json', 'w') as f:
            json.dump(bench_info, f, indent=2)

        # Backup each site
        for site in bench_info['sites']:
            site_name = site['name']
            self.console.print(f"[cyan]Backing up site {site_name}...[/cyan]")
            site_dir = sites_backup_dir / site_name
            site_dir.mkdir(parents=True)
            
            try:
                # Run backup with specific paths
                cmd_args = [
                    "bench",
                    "--site", site_name,
                    "backup",
                    "--backup-path", f"{site_dir}",
                ]
                if not self.exclude_files:
                    cmd_args.append("--with-files")
                result = subprocess.run(
                    cmd_args,
                    cwd=bench_path,
                    capture_output=True,
                    text=True,  # This ensures output is returned as string
                    check=True
                )
                if result.stderr:
                    self.console.print(f"[yellow]{result.stderr}[/yellow]")
                if result.stdout:
                    self.console.print(f"[cyan]{result.stdout}[/cyan]")
                db_backup = next(site_dir.glob("*-database.sql.gz"), None)
                files_backup = next(site_dir.glob("*-files.tar"), None)
                private_files_backup = next(site_dir.glob("*-private-files.tar"), None)

                # Update site metadata with backup paths
                site['backup_paths'] = {
                    'database': str(db_backup.relative_to(backup_dir)) if db_backup else '',
                    'files': str(files_backup.relative_to(backup_dir)) if files_backup else '',
                    'private_files': str(private_files_backup.relative_to(backup_dir)) if private_files_backup else ''
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.console.print(f"[red]Error backing up site {site_name}: {e}[/red]")

        # Update bench_info with the new site metadata
        with open(backup_dir / 'bench_info.json', 'w') as f:
            json.dump(bench_info, f, indent=2)

        # Compress directory if requested
        if self.compress:
            archive = shutil.make_archive(str(backup_dir), 'gztar', root_dir=backup_dir)
            shutil.rmtree(backup_dir)
            return Path(archive)
        return backup_dir

    def backup_benches(self) -> Union[Path, List[Path], None]:
        """Backup one or all benches under the bench directory."""
        results: List[Path] = []
        for path in self.benches:
            try:
                result = self.backup_single_bench(path)
                results.append(result)
                self.console.print(f"[green]Backed up {path.name} -> {result}[/green]")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.console.print(f"[red]Failed to backup {path.name}: {e}[/red]")

        return results

def backup_bench(
    bench_path: Path = None,
    output_dir: Path = None,
    compress: bool = True,
    exclude_files: bool = False,
    backup_folder: Optional[str] = None,
    benches_folder: Optional[str] = None
):
    manager = BenchBackupManager(
        bench_dir=bench_path or benches_folder,
        output_dir=output_dir,
        compress=compress,
        exclude_files=exclude_files,
        backup_folder=backup_folder
    )
    if not benches_folder:
        return manager.backup_single_bench(bench_path=bench_path)
    return manager.backup_benches()

def backup_all_benches(
    benches_folder: Union[str, Path],
    output_dir: Union[str, Path],
    compress: bool = True,
    exclude_files: bool = False,
    backup_folder: Optional[str] = None
) -> List[Path]:
    """
    Backup all benches found in the specified folder.
    
    Args:
        benches_folder: Directory containing multiple benches
        output_dir: Directory to store backups
        compress: Whether to compress the backup
        exclude_files: Whether to exclude files from backup
        backup_folder: Specific folder to create backup in
        
    Returns:
        List of paths to the created backups
    """
    return backup_bench(
        output_dir=output_dir,
        compress=compress,
        exclude_files=exclude_files,
        backup_folder=backup_folder,
        benches_folder=benches_folder
    )

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Backup Frappe benches")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Single bench backup command
    single_parser = subparsers.add_parser('single', help='Backup a single bench')
    single_parser.add_argument('bench_dir', help='Directory containing the bench')
    single_parser.add_argument('output_dir', help='Directory to store backups')
    single_parser.add_argument('--no-compress', action='store_true', help='Do not compress backup')
    single_parser.add_argument('--exclude-files', action='store_true', help='Exclude files from backup')
    single_parser.add_argument('--backup-folder', help='Specific folder to create backup in')
    
    # All benches backup command
    all_parser = subparsers.add_parser('all', help='Backup all benches in a folder')
    all_parser.add_argument('benches_folder', help='Directory containing multiple benches')
    all_parser.add_argument('output_dir', help='Directory to store backups')
    all_parser.add_argument('--no-compress', action='store_true', help='Do not compress backup')
    all_parser.add_argument('--exclude-files', action='store_true', help='Exclude files from backup')
    all_parser.add_argument('--backup-folder', help='Specific folder to create backup in')
    
    args = parser.parse_args()
    
    if args.command == 'single':
        manager = BenchBackupManager(
            bench_dir=args.bench_dir,
            output_dir=args.output_dir,
            compress=not args.no_compress,
            exclude_files=args.exclude_files,
            backup_folder=args.backup_folder
        )
        result = manager.backup_single_bench(bench_path=Path(args.bench_dir))
    elif args.command == 'all':
        results = backup_all_benches(
            benches_folder=args.benches_folder,
            output_dir=args.output_dir,
            compress=not args.no_compress,
            exclude_files=args.exclude_files,
            backup_folder=args.backup_folder
        )
    else:
        parser.print_help()
