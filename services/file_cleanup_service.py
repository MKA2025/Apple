"""
File Cleanup Service Module

Provides advanced file management, cleanup, and organization 
capabilities for downloaded media files.
"""

from __future__ import annotations

import os
import re
import shutil
import logging
import asyncio
from typing import (
    List, 
    Dict, 
    Any, 
    Optional, 
    Union
)
from pathlib import Path
from datetime import datetime, timedelta

from gamdl.models import (
    FileOrganizationRule, 
    CleanupConfig, 
    MediaType
)
from gamdl.utils import (
    SingletonMeta, 
    generate_unique_filename
)

logger = logging.getLogger(__name__)

class FileCleanupService(metaclass=SingletonMeta):
    """
    Advanced file management and cleanup service
    """

    def __init__(
        self, 
        base_directory: Optional[Path] = None,
        cleanup_config: Optional[CleanupConfig] = None
    ):
        """
        Initialize file cleanup service

        Args:
            base_directory (Optional[Path]): Base directory for file operations
            cleanup_config (Optional[CleanupConfig]): Cleanup configuration
        """
        self.base_directory = base_directory or Path.home() / "Downloads" / "Gamdl"
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
        self.cleanup_config = cleanup_config or CleanupConfig()
        self._organization_rules: List[FileOrganizationRule] = []

    def add_organization_rule(
        self, 
        rule: FileOrganizationRule
    ) -> None:
        """
        Add a file organization rule

        Args:
            rule (FileOrganizationRule): File organization rule to add
        """
        self._organization_rules.append(rule)

    def remove_organization_rule(
        self, 
        rule: FileOrganizationRule
    ) -> None:
        """
        Remove a file organization rule

        Args:
            rule (FileOrganizationRule): File organization rule to remove
        """
        if rule in self._organization_rules:
            self._organization_rules.remove(rule)

    async def organize_files(
        self, 
        source_directory: Optional[Path] = None
    ) -> Dict[str, List[Path]]:
        """
        Organize files based on predefined rules

        Args:
            source_directory (Optional[Path]): Directory to organize

        Returns:
            Dict[str, List[Path]]: Organized file mapping
        """
        source_directory = source_directory or self.base_directory
        organized_files: Dict[str, List[Path]] = {}

        for file_path in source_directory.glob('**/*'):
            if file_path.is_file():
                for rule in self._organization_rules:
                    if await self._match_rule(file_path, rule):
                        destination = await self._apply_rule(file_path, rule)
                        category = rule.category or 'uncategorized'
                        
                        if category not in organized_files:
                            organized_files[category] = []
                        
                        organized_files[category].append(destination)
                        break

        return organized_files

    async def _match_rule(
        self, 
        file_path: Path, 
        rule: FileOrganizationRule
    ) -> bool:
        """
        Check if a file matches an organization rule

        Args:
            file_path (Path): File to check
            rule (FileOrganizationRule): Organization rule

        Returns:
            bool: Whether the file matches the rule
        """
        # Check file extension
        if rule.extensions and file_path.suffix.lower() not in rule.extensions:
            return False

        # Check file size
        file_size = file_path.stat().st_size
        if rule.min_size and file_size < rule.min_size:
            return False
        if rule.max_size and file_size > rule.max_size:
            return False

        # Check filename pattern
        if rule.filename_pattern:
            if not re.search(rule.filename_pattern, file_path.name):
                return False

        # Check creation/modification time
        file_stat = file_path.stat()
        current_time = datetime.now()
        
        if rule.max_age:
            file_age = current_time - datetime.fromtimestamp(file_stat.st_mtime)
            if file_age > timedelta(days=rule.max_age):
                return False

        return True

    async def _apply_rule(
        self, 
        file_path: Path, 
        rule: FileOrganizationRule
    ) -> Path:
        """
        Apply an organization rule to a file

        Args:
            file_path (Path): File to organize
            rule (FileOrganizationRule): Organization rule

        Returns:
            Path: Destination path of the organized file
        """
        # Determine destination directory
        if rule.destination_directory:
            destination_dir = Path(rule.destination_directory)
        else:
            destination_dir = self.base_directory / (rule.category or 'uncategorized')
        
        destination_dir.mkdir(parents=True, exist_ok=True)

        # Generate destination filename
        if rule.rename_template:
            new_filename = rule.rename_template.format(
                original_filename=file_path.name,
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                unique_id=generate_unique_filename()
            )
            destination_path = destination_dir / new_filename
        else:
            destination_path = destination_dir / file_path.name

        # Move or copy file
        if rule.action == 'move':
            shutil.move(str(file_path), str(destination_path))
        elif rule.action == 'copy':
            shutil.copy2(str(file_path), str(destination_path))

        return destination_path

    async def cleanup_old_files(
        self, 
        source_directory: Optional[Path] = None,
        max_age_days: Optional[int] = None
    ) -> List[Path]:
        """
        Remove files older than specified age

        Args:
            source_directory (Optional[Path]): Directory to clean
            max_age_days (Optional[int]): Maximum file age in days

        Returns:
            List[Path]: Removed files
        """
        source_directory = source_directory or self.base_directory
        max_age_days = max_age_days or self.cleanup_config.max_file_age_days
        removed_files: List[Path] = []

        current_time = datetime.now()
        for file_path in source_directory.glob('**/*'):
            if file_path.is_file():
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_age > timedelta(days=max_age_days):
                    try:
                        file_path.unlink()
                        removed_files.append(file_path)
                        logger.info(f"Removed old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove file {file_path}: {e}")

        return removed_files

    async def backup_files(
        self, 
        source_directory: Optional[Path] = None,
        backup_directory: Optional[Path] = None
    ) -> Path:
        """
        Create a backup of files in the source directory

        Args:
            source_directory (Optional[Path]): Directory to backup
            backup_directory (Optional[Path]): Backup destination directory

        Returns:
            Path: Backup directory path
        """
        source_directory = source_directory or self.base_directory
        backup_directory = backup_directory or (
            Path.home() / "Downloads" / "Gamdl_Backup" / 
            datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        backup_directory.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copytree(
                source_directory , 
                backup_directory, 
                dirs_exist_ok=True
            )
            logger.info(f"Backup created at: {backup_directory}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

        return backup_directory

# Public API
__all__ = [
    'FileCleanupService'
]
