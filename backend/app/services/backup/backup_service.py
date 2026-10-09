"""
Database backup and restore service.
Utilizes PostgreSQL native utilities with enhanced security and path handling.
"""

import subprocess
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from yarl import URL
from app.core.config import settings

logger = logging.getLogger(__name__)

class BackupService:
    """Manages clinical database snapshots and restoration processes."""

    def __init__(self, backup_path: str = "backups") -> None:
        self.backup_dir = Path(backup_path)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, database_url: str) -> str:
        """
        Generates a compressed PostgreSQL custom-format backup.
        Returns the absolute path to the generated .bak file.
        """
        # Use timezone-aware UTC for 2026 compliance
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"clinical_snapshot_{timestamp}.bak"

        try:
            # Securely parse the connection string using yarl
            url = URL(database_url)
            
            # Prepare environment with credentials safely isolated
            env = os.environ.copy()
            if url.password:
                env['PGPASSWORD'] = url.password

            # pg_dump command using 'Custom' format for better portability/compression
            command = [
                'pg_dump',
                '-h', url.host or 'localhost',
                '-p', str(url.port or 5432),
                '-U', url.user or 'postgres',
                '-d', url.path.lstrip('/'),
                '-F', 'c',  # Custom format (compressed and blob-ready)
                '-f', str(backup_file)
            ]

            subprocess.run(command, env=env, check=True, capture_output=True)
            
            logger.info(f"✅ Clinical database snapshot created: {backup_file}")
            return str(backup_file.absolute())

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ pg_dump failed: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"❌ Backup orchestration failed: {e}")
            raise

    def restore_backup(self, backup_file: str, database_url: str) -> bool:
        """
        Restores the database from a custom-format backup.
        Uses pg_restore for high-performance data recovery.
        """
        file_path = Path(backup_file)
        if not file_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        try:
            url = URL(database_url)
            env = os.environ.copy()
            if url.password:
                env['PGPASSWORD'] = url.password

            # pg_restore is required for the 'Custom' format snapshots
            command = [
                'pg_restore',
                '-h', url.host or 'localhost',
                '-p', str(url.port or 5432),
                '-U', url.user or 'postgres',
                '-d', url.path.lstrip('/'),
                '--clean',        # Drop existing objects before creating
                '--if-exists',    # Don't error if objects don't exist
                '--no-owner',     # Skip restoration of object ownership
                str(file_path)
            ]

            subprocess.run(command, env=env, check=True, capture_output=True)
            logger.info(f"✅ Clinical database restored from: {backup_file}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ pg_restore failed: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"❌ Restore orchestration failed: {e}")
            raise

    def list_backups(self) -> List[Path]:
        """Retrieves all available snapshots, sorted by most recent first."""
        backups = list(self.backup_dir.glob("clinical_snapshot_*.bak"))
        return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)

    def rotate_backups(self, keep_last: int = 10) -> None:
        """Retention policy: Deletes older snapshots to conserve storage."""
        backups = self.list_backups()
        
        if len(backups) > keep_last:
            for old_backup in backups[keep_last:]:
                old_backup.unlink()
                logger.info(f"Deleted expired clinical snapshot: {old_backup.name}")

# Global Singleton for use in Admin routes
backup_service = BackupService()