"""
File management utilities for the Financial Document Analyzer
Handles file persistence, cleanup, and storage management
"""
import os
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.core.database import get_database_manager
from backend.services.services import DocumentService, UserService

logger = logging.getLogger(__name__)

class FileManager:
    """Manage file storage and cleanup operations"""
    
    def __init__(self, upload_dir: str = "data", persistent_dir: str = "storage"):
        self.upload_dir = Path(upload_dir)
        self.persistent_dir = Path(persistent_dir)
        self.max_files_per_user = int(os.getenv('MAX_STORED_FILES_PER_USER', 10))
        self.cleanup_days = int(os.getenv('FILE_CLEANUP_DAYS', 7))
        
        # Ensure directories exist
        self.upload_dir.mkdir(exist_ok=True)
        self.persistent_dir.mkdir(exist_ok=True)
        
        logger.info(f"FileManager initialized - Upload: {self.upload_dir}, Persistent: {self.persistent_dir}")
    
    def move_to_persistent_storage(self, temp_file_path: str, document_id: str, user_id: str) -> str:
        """Move a temporary file to persistent storage"""
        try:
            temp_path = Path(temp_file_path)
            if not temp_path.exists():
                logger.warning(f"Temporary file not found: {temp_file_path}")
                return None
            
            # Create user directory in persistent storage
            user_dir = self.persistent_dir / user_id
            user_dir.mkdir(exist_ok=True)
            
            # Generate persistent filename
            file_extension = temp_path.suffix
            persistent_filename = f"{document_id}{file_extension}"
            persistent_path = user_dir / persistent_filename
            
            # Move file to persistent storage
            shutil.move(str(temp_path), str(persistent_path))
            logger.info(f"Moved file to persistent storage: {persistent_path}")
            
            return str(persistent_path)
            
        except Exception as e:
            logger.error(f"Error moving file to persistent storage: {e}")
            return None
    
    def get_file_path(self, document_id: str, user_id: str) -> Optional[str]:
        """Get the file path for a stored document"""
        try:
            user_dir = self.persistent_dir / user_id
            
            # Look for the file with any extension
            for file_path in user_dir.glob(f"{document_id}.*"):
                if file_path.is_file():
                    return str(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting file path: {e}")
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def cleanup_temporary_files(self) -> int:
        """Clean up old temporary files in upload directory"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)  # Delete files older than 24 hours
            deleted_count = 0
            
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.info(f"Cleaned up temporary file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete temporary file {file_path}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during temporary file cleanup: {e}")
            return 0
    
    def cleanup_user_files(self, user_id: str, keep_recent: int = None) -> int:
        """Clean up user files, keeping only the most recent ones"""
        try:
            keep_recent = keep_recent or self.max_files_per_user
            user_dir = self.persistent_dir / user_id
            
            if not user_dir.exists():
                return 0
            
            # Get all user files with their modification times
            user_files = []
            for file_path in user_dir.iterdir():
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    user_files.append((file_path, mtime))
            
            # Sort by modification time (newest first)
            user_files.sort(key=lambda x: x[1], reverse=True)
            
            # Delete files beyond the keep limit
            deleted_count = 0
            if len(user_files) > keep_recent:
                files_to_delete = user_files[keep_recent:]
                for file_path, _ in files_to_delete:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old user file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete user file {file_path}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during user file cleanup: {e}")
            return 0
    
    def cleanup_orphaned_files(self) -> int:
        """Clean up files that don't have corresponding database records"""
        try:
            deleted_count = 0
            db_manager = get_database_manager()
            
            with db_manager.session_scope() as session:
                # Get all documents from database
                all_documents = session.query(DocumentService.get_document_by_id.__self__.__class__).all()
                
                # Create set of valid file paths
                valid_paths = set()
                for doc in all_documents:
                    if doc.file_path and doc.is_stored_permanently:
                        valid_paths.add(doc.file_path)
                
                # Check persistent storage directories
                for user_dir in self.persistent_dir.iterdir():
                    if user_dir.is_dir():
                        for file_path in user_dir.iterdir():
                            if file_path.is_file() and str(file_path) not in valid_paths:
                                try:
                                    file_path.unlink()
                                    deleted_count += 1
                                    logger.info(f"Deleted orphaned file: {file_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete orphaned file {file_path}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} orphaned files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during orphaned file cleanup: {e}")
            return 0
    
    def get_storage_statistics(self) -> dict:
        """Get storage usage statistics"""
        try:
            stats = {
                "temporary_files": {"count": 0, "size_bytes": 0},
                "persistent_files": {"count": 0, "size_bytes": 0},
                "total_size_mb": 0
            }
            
            # Count temporary files
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    stats["temporary_files"]["count"] += 1
                    stats["temporary_files"]["size_bytes"] += file_path.stat().st_size
            
            # Count persistent files
            for user_dir in self.persistent_dir.iterdir():
                if user_dir.is_dir():
                    for file_path in user_dir.iterdir():
                        if file_path.is_file():
                            stats["persistent_files"]["count"] += 1
                            stats["persistent_files"]["size_bytes"] += file_path.stat().st_size
            
            total_bytes = stats["temporary_files"]["size_bytes"] + stats["persistent_files"]["size_bytes"]
            stats["total_size_mb"] = round(total_bytes / 1024 / 1024, 2)
            
            # Add human-readable sizes
            stats["temporary_files"]["size_mb"] = round(stats["temporary_files"]["size_bytes"] / 1024 / 1024, 2)
            stats["persistent_files"]["size_mb"] = round(stats["persistent_files"]["size_bytes"] / 1024 / 1024, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {}
    
    def perform_maintenance(self) -> dict:
        """Perform comprehensive file system maintenance"""
        try:
            logger.info("Starting file system maintenance...")
            
            results = {
                "temporary_files_cleaned": self.cleanup_temporary_files(),
                "orphaned_files_cleaned": self.cleanup_orphaned_files(),
                "user_files_cleaned": 0
            }
            
            # Clean up files for inactive users
            db_manager = get_database_manager()
            with db_manager.session_scope() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=self.cleanup_days)
                inactive_users = session.query(UserService.get_user_by_id.__self__.__class__).filter(
                    UserService.get_user_by_id.__self__.__class__.last_activity < cutoff_date
                ).all()
                
                for user in inactive_users:
                    cleaned = self.cleanup_user_files(user.id, 0)  # Delete all files for inactive users
                    results["user_files_cleaned"] += cleaned
            
            results["storage_stats"] = self.get_storage_statistics()
            
            logger.info(f"File system maintenance completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during file system maintenance: {e}")
            return {"error": str(e)}

# Global file manager instance
file_manager = FileManager()

def get_file_manager() -> FileManager:
    """Get the global file manager instance"""
    return file_manager

def schedule_maintenance():
    """Schedule regular maintenance tasks"""
    # This would be called periodically, e.g., by a background task or cron job
    return file_manager.perform_maintenance()
