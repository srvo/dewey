"""Database synchronization module.

This module handles data synchronization between local DuckDB and MotherDuck cloud databases.
It implements conflict detection, resolution, and change tracking.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from .connection import db_manager
from .errors import SyncError, handle_error
from .schema import TABLES

logger = logging.getLogger(__name__)

class SyncManager:
    """Manages synchronization between local and MotherDuck databases."""
    
    def __init__(self):
        """Initialize the sync manager."""
        self.offline_changes = []
        self.sync_in_progress = False
        
    def queue_offline_change(self, change: Dict[str, Any]):
        """Queue a change for later sync when online.
        
        Args:
            change: Change details to queue
        """
        self.offline_changes.append(change)
        logger.info(f"Queued offline change for {change['table_name']}.{change['record_id']}")
        
    def sync_offline_changes(self) -> int:
        """Attempt to sync queued offline changes.
        
        Returns:
            Number of changes successfully synced
        """
        if not self.offline_changes:
            return 0
            
        if not db_manager.is_online():
            return 0
            
        synced = 0
        remaining = []
        
        for change in self.offline_changes:
            try:
                apply_changes(change['table_name'], [change], target_local=False)
                synced += 1
                logger.info(f"Synced offline change for {change['table_name']}.{change['record_id']}")
            except Exception as e:
                logger.error(f"Failed to sync offline change: {e}")
                remaining.append(change)
                
        self.offline_changes = remaining
        return synced

def record_sync_status(status: str, message: str, details: Optional[Dict] = None):
    """Record sync status in the sync_status table.
    
    Args:
        status: Status of the sync operation
        message: Status message
        details: Additional details as JSON
    """
    try:
        db_manager.execute_query("""
            INSERT INTO sync_status (status, message, details)
            VALUES (?, ?, ?)
        """, [status, message, details], for_write=True, local_only=True)
    except Exception as e:
        error_id = handle_error(e, {
            'status': status,
            'message': message,
            'details': details
        })
        logger.error(f"Failed to record sync status (Error ID: {error_id})")

def get_last_sync_time() -> Optional[datetime]:
    """Get the timestamp of the last successful sync.
    
    Returns:
        Timestamp of last successful sync or None if no sync found
    """
    try:
        result = db_manager.execute_query("""
            SELECT sync_time FROM sync_status
            WHERE status = 'success'
            ORDER BY sync_time DESC
            LIMIT 1
        """, local_only=True)
        
        return result[0][0] if result else None
    except Exception as e:
        error_id = handle_error(e, {'context': 'get_last_sync_time'})
        logger.error(f"Failed to get last sync time (Error ID: {error_id})")
        return None

def get_changes_since(table_name: str, since: datetime, local_only: bool = False) -> List[Dict]:
    """Get changes made to a table since the given timestamp.
    
    Args:
        table_name: Name of the table to check
        since: Timestamp to check changes from
        local_only: Whether to only check local database
        
    Returns:
        List of changes as dictionaries
    """
    try:
        changes = db_manager.execute_query("""
            SELECT * FROM change_log
            WHERE table_name = ?
            AND changed_at > ?
            ORDER BY changed_at ASC
        """, [table_name, since], local_only=local_only)
        
        return [dict(zip(['id', 'table_name', 'operation', 'record_id', 
                         'changed_at', 'user_id', 'details'], row)) 
                for row in changes]
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'since': since,
            'local_only': local_only
        })
        logger.error(f"Failed to get changes (Error ID: {error_id})")
        return []

def detect_conflicts(table_name: str, local_changes: List[Dict], 
                    remote_changes: List[Dict]) -> List[Dict]:
    """Detect conflicts between local and remote changes.
    
    Args:
        table_name: Name of the table being checked
        local_changes: List of local changes
        remote_changes: List of remote changes
        
    Returns:
        List of conflicts as dictionaries
    """
    conflicts = []
    
    # Group changes by record_id
    local_by_id = {c['record_id']: c for c in local_changes}
    remote_by_id = {c['record_id']: c for c in remote_changes}
    
    # Find records modified in both databases
    common_ids = set(local_by_id.keys()) & set(remote_by_id.keys())
    
    for record_id in common_ids:
        local = local_by_id[record_id]
        remote = remote_by_id[record_id]
        
        # Check for conflicting operations
        if local['operation'] != remote['operation']:
            conflicts.append({
                'table_name': table_name,
                'record_id': record_id,
                'operation': 'conflict',
                'error_message': f"Conflicting operations: local={local['operation']}, remote={remote['operation']}",
                'details': {
                    'local': local,
                    'remote': remote,
                    'conflict_type': 'operation_mismatch'
                }
            })
        elif local['operation'] in ('UPDATE', 'INSERT'):
            # Check for data conflicts in updates
            local_data = local.get('details', {})
            remote_data = remote.get('details', {})
            
            # Find conflicting fields
            conflicts_fields = []
            for field in set(local_data.keys()) & set(remote_data.keys()):
                if local_data[field] != remote_data[field]:
                    conflicts_fields.append(field)
                    
            if conflicts_fields:
                conflicts.append({
                    'table_name': table_name,
                    'record_id': record_id,
                    'operation': 'conflict',
                    'error_message': f"Conflicting field values: {', '.join(conflicts_fields)}",
                    'details': {
                        'local': local,
                        'remote': remote,
                        'conflict_type': 'data_mismatch',
                        'conflict_fields': conflicts_fields
                    }
                })
                
    return conflicts

def resolve_conflicts(conflicts: List[Dict]) -> None:
    """Record conflicts for manual resolution.
    
    Args:
        conflicts: List of conflicts to record
    """
    try:
        for conflict in conflicts:
            db_manager.execute_query("""
                INSERT INTO sync_conflicts (
                    table_name, record_id, operation, error_message,
                    sync_time, resolved, resolution_details
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, FALSE, ?)
            """, [
                conflict['table_name'],
                conflict['record_id'],
                conflict['operation'],
                conflict['error_message'],
                conflict.get('details')
            ], for_write=True, local_only=True)
            
            logger.warning(f"Recorded conflict for {conflict['table_name']}.{conflict['record_id']}")
    except Exception as e:
        error_id = handle_error(e, {'conflicts': conflicts})
        logger.error(f"Failed to record conflicts (Error ID: {error_id})")

def apply_changes(table_name: str, changes: List[Dict], target_local: bool = True) -> None:
    """Apply changes to the target database.
    
    Args:
        table_name: Name of the table to update
        changes: List of changes to apply
        target_local: Whether to apply to local database (True) or MotherDuck (False)
    """
    try:
        for change in changes:
            operation = change['operation']
            record_id = change['record_id']
            details = change.get('details', {})
            
            if operation == 'INSERT':
                columns = ', '.join(details.keys())
                placeholders = ', '.join(['?' for _ in details])
                values = list(details.values())
                
                db_manager.execute_query(f"""
                    INSERT INTO {table_name} ({columns})
                    VALUES ({placeholders})
                """, values, for_write=True, local_only=target_local)
                
            elif operation == 'UPDATE':
                set_clause = ', '.join([f"{k} = ?" for k in details])
                values = list(details.values()) + [record_id]
                
                db_manager.execute_query(f"""
                    UPDATE {table_name}
                    SET {set_clause}
                    WHERE id = ?
                """, values, for_write=True, local_only=target_local)
                
            elif operation == 'DELETE':
                db_manager.execute_query(f"""
                    DELETE FROM {table_name}
                    WHERE id = ?
                """, [record_id], for_write=True, local_only=target_local)
                
            logger.info(f"Applied {operation} to {table_name}.{record_id}")
            
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'target_local': target_local
        })
        raise SyncError(f"Failed to apply changes (Error ID: {error_id})")

def sync_table(table_name: str, since: datetime) -> Tuple[int, int]:
    """Synchronize a single table between local and MotherDuck.
    
    Args:
        table_name: Name of the table to sync
        since: Timestamp to sync changes from
        
    Returns:
        Tuple of (changes_applied, conflicts_found)
    """
    try:
        # Get changes from both databases
        local_changes = get_changes_since(table_name, since, local_only=True)
        remote_changes = get_changes_since(table_name, since, local_only=False)
        
        # Detect conflicts
        conflicts = detect_conflicts(table_name, local_changes, remote_changes)
        
        if conflicts:
            # Record conflicts for manual resolution
            resolve_conflicts(conflicts)
            logger.warning(f"Found {len(conflicts)} conflicts in {table_name}")
            
        # Apply non-conflicting changes
        local_ids = {c['record_id'] for c in local_changes}
        remote_ids = {c['record_id'] for c in remote_changes}
        conflict_ids = {c['record_id'] for c in conflicts}
        
        # Changes to apply to MotherDuck
        to_remote = [c for c in local_changes 
                    if c['record_id'] not in conflict_ids
                    and c['record_id'] not in remote_ids]
                    
        # Changes to apply to local
        to_local = [c for c in remote_changes
                   if c['record_id'] not in conflict_ids
                   and c['record_id'] not in local_ids]
        
        # Apply changes
        if to_remote and db_manager.is_online():
            apply_changes(table_name, to_remote, target_local=False)
        elif to_remote:
            # Queue changes for later sync
            sync_manager.queue_offline_change(to_remote)
            
        if to_local:
            apply_changes(table_name, to_local, target_local=True)
            
        changes_applied = len(to_remote) + len(to_local)
        logger.info(f"Synced {changes_applied} changes for {table_name}")
        
        return changes_applied, len(conflicts)
        
    except Exception as e:
        error_id = handle_error(e, {
            'table_name': table_name,
            'since': since
        })
        raise SyncError(f"Failed to sync table (Error ID: {error_id})")

def sync_all_tables(max_age: Optional[timedelta] = None) -> Dict[str, Tuple[int, int]]:
    """Synchronize all tables between local and MotherDuck.
    
    Args:
        max_age: Maximum age of changes to sync, defaults to None (sync all)
        
    Returns:
        Dictionary mapping table names to (changes_applied, conflicts_found)
    """
    try:
        # Get last sync time
        last_sync = get_last_sync_time()
        if not last_sync and not max_age:
            max_age = timedelta(days=7)  # Default to 7 days if no sync history
            
        since = max(last_sync, datetime.now() - max_age) if max_age else last_sync
        
        # Start sync
        record_sync_status('started', f"Starting sync from {since}")
        results = {}
        
        # Try to sync offline changes first
        if db_manager.is_online():
            synced_offline = sync_manager.sync_offline_changes()
            if synced_offline:
                logger.info(f"Synced {synced_offline} offline changes")
        
        # Sync each table
        for table_name in TABLES:
            try:
                changes, conflicts = sync_table(table_name, since)
                results[table_name] = (changes, conflicts)
            except Exception as e:
                logger.error(f"Failed to sync {table_name}: {e}")
                record_sync_status('error', f"Failed to sync {table_name}: {e}")
                continue
                
        # Record successful sync
        total_changes = sum(r[0] for r in results.values())
        total_conflicts = sum(r[1] for r in results.values())
        record_sync_status('success', 
                          f"Synced {total_changes} changes, found {total_conflicts} conflicts",
                          {'results': results})
                          
        return results
        
    except Exception as e:
        error_id = handle_error(e, {'max_age': str(max_age) if max_age else None})
        error_msg = f"Sync failed (Error ID: {error_id})"
        logger.error(error_msg)
        record_sync_status('error', error_msg)
        raise SyncError(error_msg)

# Global instances
sync_manager = SyncManager() 