"""
Administrative endpoints for clinical database backup and restoration.
Strictly restricted to users with the 'admin' role.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.deps import get_current_admin_user
from app.db.models import User
from app.services.backup.backup_service import backup_service
from app.core.config import settings

router = APIRouter(prefix="/admin/backups", tags=["Infrastructure Management"])

# Modern Dependency Alias for Admin Authorization
AdminDep = Annotated[User, Depends(get_current_admin_user)]

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_database_backup(current_admin: AdminDep):
    """
    Triggers an immediate PostgreSQL custom-format snapshot.
    Restricted to system administrators.
    """
    try:
        # Utilizing the modernized BackupService with custom format support
        backup_path = backup_service.create_backup(settings.DATABASE_URL)
        return {
            "status": "success",
            "message": "Clinical database snapshot generated",
            "path": backup_path
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Backup execution failed: {str(e)}"
        )

@router.get("/list")
async def list_available_backups(current_admin: AdminDep):
    """
    Retrieves a list of all existing clinical database snapshots.
    Sorted by most recent first.
    """
    backups = backup_service.list_backups()
    return {
        "snapshots": [str(b.name) for b in backups],
        "count": len(backups),
        "directory": str(backup_service.backup_dir)
    }

@router.post("/restore")
async def restore_database_from_backup(
    backup_filename: str,
    current_admin: AdminDep
):
    """
    Restores the clinical database from a specified snapshot file.
    Warning: This operation will drop and recreate existing database objects.
    """
    try:
        # Reconstruct path safely within the backup directory
        target_file = backup_service.backup_dir / backup_filename
        
        backup_service.restore_backup(str(target_file), settings.DATABASE_URL)
        return {"status": "success", "message": "Clinical database successfully restored"}
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Specified backup file does not exist"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Restore operation failed: {str(e)}"
        )

@router.post("/rotate", status_code=status.HTTP_200_OK)
async def rotate_old_backups(
    current_admin: AdminDep,
    keep_last: Annotated[int, Query(ge=1, le=50)] = 10
):
    """
    Manually triggers the backup retention policy.
    Removes older snapshots while keeping the most recent 'N' files.
    """
    try:
        # Utilizing the renamed 'rotate_backups' method from the refactored service
        backup_service.rotate_backups(keep_last=keep_last)
        return {
            "status": "success", 
            "message": f"Backup rotation complete. Retention set to last {keep_last} snapshots."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Rotation failed: {str(e)}"
        )