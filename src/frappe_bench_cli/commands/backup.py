import os
import json
import shutil
import tarfile
import subprocess
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from git import Repo
from bench.utils.system import run_frappe_cmd


class BenchBackupManager:
    def __init__(
        self,
        bench_dir: Union[str, Path],
        output_dir: Union[str, Path],
        compress: bool = True
    ):
        self.bench_dir = Path(bench_dir)
        self.output_dir = Path(output_dir)
        self.compress = compress
        self.console = Console()

        if not self.bench_dir.exists():
            raise FileNotFoundError(f"Bench directory not found: {self.bench_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sites(self) -> List[str]:
        return [
            path
            for path in os.listdir(os.path.join(self.bench_dir, "sites"))
            if os.path.exists(os.path.join(self.bench_dir, "sites", path, "site_config.json"))
        ]
    @staticmethod
    def is_valid_bench(bench_path: Path) -> bool:
        """Check if the given path is a valid Frappe bench."""
        return (
            bench_path.exists() and
            (bench_path / 'apps').exists() and
            (bench_path / 'sites').exists()
        )

    def get_bench_info(self, bench_path: Path) -> Dict[str, Any]:
        """Extract information about a bench including apps and sites."""
        if not self.is_valid_bench(bench_path):
            raise ValueError(f"{bench_path} is not a valid Frappe bench")

        info: Dict[str, Any] = {'name': bench_path.name, 'apps': [], 'sites': []}

        # Collect apps info
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
            for site in self.sites
        ]

        return info

    def backup_single_bench(self, bench_path: Path) -> Path:
        """Backup a single bench to the output directory."""
        bench_info = self.get_bench_info(bench_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{bench_info['name']}_{timestamp}"
        backup_dir = self.output_dir / backup_name
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
                run_frappe_cmd(
                    "--site", site_name,
                    "backup",
                    "--backup-path", site_dir,
                    bench_path=bench_path
                )
            except Exception as e:
                self.console.print(f"[red]Error backing up site {site_name}: {e}[/red]")

        # Compress directory if requested
        if self.compress:
            archive = shutil.make_archive(str(backup_dir), 'gztar', root_dir=backup_dir)
            shutil.rmtree(backup_dir)
            return Path(archive)
        return backup_dir

    def backup_benches(self, bench_name: Optional[str] = None) -> Union[Path, List[Path], None]:
        """Backup one or all benches under the bench directory."""
        if bench_name:
            path = self.bench_dir / bench_name
            if not self.is_valid_bench(path):
                raise ValueError(f"{path} is not a valid Frappe bench")
            return self.backup_single_bench(path)

        # Discover all benches
        benches = [d for d in self.bench_dir.iterdir() if d.is_dir() and self.is_valid_bench(d)]
        if not benches:
            self.console.print("[yellow]No valid Frappe benches found[/yellow]")
            return None

        results: List[Path] = []
        with Progress() as progress:
            task = progress.add_task("[cyan]Backing up benches...", total=len(benches))
            for bench_path in benches:
                try:
                    result = self.backup_single_bench(bench_path)
                    results.append(result)
                    self.console.print(f"[green]Backed up {bench_path.name} -> {result}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Failed to backup {bench_path.name}: {e}[/red]")
                progress.advance(task)
        return results


def backup_bench(
    bench_path: Path,
    output_dir: Path,
    compress: bool
):
    manager = BenchBackupManager(
        bench_dir=bench_path,
        output_dir=output_dir,
        compress=compress
    )
    return manager.backup_single_bench(bench_path=bench_path) 

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Backup Frappe benches")
    parser.add_argument('bench_dir', help='Directory containing benches')
    parser.add_argument('output_dir', help='Directory to store backups')
    parser.add_argument('--bench', help='Name of a specific bench to backup')
    parser.add_argument('--no-compress', action='store_true', help='Do not compress backup')
    args = parser.parse_args()

    manager = BenchBackupManager(
        bench_dir=args.bench_dir,
        output_dir=args.output_dir,
        compress=not args.no_compress
    )
    result = manager.backup_single_bench(bench_path=args.bench_dir)
    print(result)
