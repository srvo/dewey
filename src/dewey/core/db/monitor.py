"""Database monitoring module.

This module provides monitoring and health check functionality for both
local DuckDB and MotherDuck cloud databases.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import threading

from .config import get_db_config
from .connection import db_manager, DatabaseConnectionError
from .schema import TABLES
from .sync import get_last_sync_time

logger = logging.getLogger(__name__)

# Global flag to control monitoring thread
_monitoring_active = False
_monitor_thread = None

class HealthCheckError(Exception):
    """Exception raised for health check errors."""
    pass

def stop_monitoring() -> None:
    """Stop the monitoring thread."""
    global _monitoring_active, _monitor_thread
    logger.info("Stopping database monitoring")
    _monitoring_active = False
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=5)
    logger.info("Database monitoring stopped")

def check_connection(local_only: bool = False) -> bool:
    """Check database connection health.
    
    Args:
        local_only: Whether to only check local database
        
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        # Try to execute a simple query
        result = db_manager.execute_query(
            "SELECT 1", local_only=local_only
        )
        return bool(result and result[0][0] == 1)
    except Exception as e:
        logger.error(f"Connection check failed: {e}")
        return False

def check_table_health(table_name: str, local_only: bool = False) -> Dict:
    """Check health of a specific table.
    
    Args:
        table_name: Name of the table to check
        local_only: Whether to only check local database
        
    Returns:
        Dictionary containing table health information
    """
    try:
        # Get table statistics
        stats = db_manager.execute_query(f"""
            SELECT COUNT(*) as row_count,
                   SUM(CASE WHEN id IS NULL THEN 1 ELSE 0 END) as null_ids,
                   MIN(created_at) as oldest_record,
                   MAX(created_at) as newest_record
            FROM {table_name}
        """, local_only=local_only)
        
        if not stats or not stats[0]:
            raise HealthCheckError(f"Failed to get statistics for {table_name}")
            
        row_count, null_ids, oldest, newest = stats[0]
        
        # Check for data integrity issues
        issues = []
        
        if null_ids > 0:
            issues.append(f"Found {null_ids} records with NULL IDs")
            
        if row_count == 0:
            issues.append("Table is empty")
            
        # Check for duplicate IDs
        dupes = db_manager.execute_query(f"""
            SELECT id, COUNT(*) as count
            FROM {table_name}
            GROUP BY id
            HAVING COUNT(*) > 1
        """, local_only=local_only)
        
        if dupes:
            issues.append(f"Found {len(dupes)} duplicate IDs")
            
        return {
            'table_name': table_name,
            'row_count': row_count,
            'null_ids': null_ids,
            'oldest_record': oldest.isoformat() if oldest else None,
            'newest_record': newest.isoformat() if newest else None,
            'has_duplicates': bool(dupes),
            'duplicate_count': len(dupes) if dupes else 0,
            'issues': issues,
            'healthy': not issues
        }
        
    except Exception as e:
        error_msg = f"Health check failed for {table_name}: {e}"
        logger.error(error_msg)
        return {
            'table_name': table_name,
            'error': str(e),
            'healthy': False
        }

def check_sync_health() -> Dict:
    """Check health of database synchronization.
    
    Returns:
        Dictionary containing sync health information
    """
    try:
        last_sync = get_last_sync_time()
        config = get_db_config()
        sync_interval = timedelta(seconds=config['sync_interval'])
        
        # Check if sync is overdue
        is_overdue = False
        if last_sync:
            time_since_sync = datetime.now() - last_sync
            is_overdue = time_since_sync > sync_interval
            
        # Check for conflicts
        conflicts = db_manager.execute_query("""
            SELECT COUNT(*) FROM sync_conflicts
            WHERE resolved = FALSE
        """)
        
        unresolved_conflicts = conflicts[0][0] if conflicts else 0
        
        # Check for failed syncs
        failed_syncs = db_manager.execute_query("""
            SELECT COUNT(*) FROM sync_status
            WHERE status = 'error'
            AND sync_time > CURRENT_TIMESTAMP - INTERVAL '24 HOURS'
        """)
        
        recent_failures = failed_syncs[0][0] if failed_syncs else 0
        
        return {
            'last_sync': last_sync.isoformat() if last_sync else None,
            'sync_interval': str(sync_interval),
            'is_overdue': is_overdue,
            'unresolved_conflicts': unresolved_conflicts,
            'recent_failures': recent_failures,
            'healthy': not (is_overdue or unresolved_conflicts or recent_failures)
        }
        
    except Exception as e:
        error_msg = f"Sync health check failed: {e}"
        logger.error(error_msg)
        return {
            'error': str(e),
            'healthy': False
        }

def check_schema_consistency() -> Dict:
    """Check schema consistency between local and MotherDuck databases.
    
    Returns:
        Dictionary containing schema consistency information
    """
    try:
        inconsistencies = []
        
        for table_name in TABLES:
            # Get schema from both databases
            local_schema = db_manager.execute_query(
                f"DESCRIBE {table_name}", local_only=True
            )
            remote_schema = db_manager.execute_query(
                f"DESCRIBE {table_name}", local_only=False
            )
            
            # Compare schemas
            if local_schema != remote_schema:
                # Find specific differences
                local_cols = {row[0]: row for row in local_schema}
                remote_cols = {row[0]: row for row in remote_schema}
                
                # Check for missing columns
                local_missing = set(remote_cols.keys()) - set(local_cols.keys())
                remote_missing = set(local_cols.keys()) - set(remote_cols.keys())
                
                # Check for type mismatches
                type_mismatches = []
                for col in set(local_cols.keys()) & set(remote_cols.keys()):
                    if local_cols[col] != remote_cols[col]:
                        type_mismatches.append({
                            'column': col,
                            'local_type': local_cols[col][1],
                            'remote_type': remote_cols[col][1]
                        })
                
                inconsistencies.append({
                    'table': table_name,
                    'local_missing': list(local_missing),
                    'remote_missing': list(remote_missing),
                    'type_mismatches': type_mismatches
                })
                
        return {
            'consistent': not inconsistencies,
            'inconsistencies': inconsistencies
        }
        
    except Exception as e:
        error_msg = f"Schema consistency check failed: {e}"
        logger.error(error_msg)
        return {
            'error': str(e),
            'consistent': False
        }

def check_database_size() -> Dict:
    """Check database size and growth.
    
    Returns:
        Dictionary containing database size information
    """
    try:
        # Get table sizes
        sizes = {}
        total_rows = 0
        
        for table_name in TABLES:
            result = db_manager.execute_query(f"""
                SELECT COUNT(*) as row_count,
                       SUM(LENGTH(CAST(* AS VARCHAR))) as approx_size
                FROM {table_name}
            """)
            
            if result and result[0]:
                row_count, approx_size = result[0]
                total_rows += row_count
                sizes[table_name] = {
                    'row_count': row_count,
                    'approx_size_bytes': approx_size or 0
                }
                
        # Get database file size
        db_size = os.path.getsize(get_db_config()['local_db_path'])
        
        # Calculate size metrics
        total_data_size = sum(t['approx_size_bytes'] for t in sizes.values())
        avg_row_size = total_data_size / total_rows if total_rows > 0 else 0
        
        return {
            'file_size_bytes': db_size,
            'total_rows': total_rows,
            'total_data_size_bytes': total_data_size,
            'average_row_size_bytes': avg_row_size,
            'table_sizes': sizes
        }
        
    except Exception as e:
        error_msg = f"Size check failed: {e}"
        logger.error(error_msg)
        return {
            'error': str(e)
        }

def check_query_performance() -> Dict:
    """Check database query performance.
    
    Returns:
        Dictionary containing performance metrics
    """
    try:
        metrics = {}
        
        # Test simple query performance
        start_time = time.time()
        db_manager.execute_query("SELECT 1")
        simple_query_time = time.time() - start_time
        
        # Test table scan performance
        table_metrics = {}
        for table_name in TABLES:
            start_time = time.time()
            result = db_manager.execute_query(f"""
                SELECT COUNT(*) FROM {table_name}
            """)
            scan_time = time.time() - start_time
            
            row_count = result[0][0] if result else 0
            rows_per_sec = row_count / scan_time if scan_time > 0 else 0
            
            table_metrics[table_name] = {
                'scan_time_seconds': scan_time,
                'row_count': row_count,
                'rows_per_second': rows_per_sec
            }
            
        return {
            'simple_query_time_seconds': simple_query_time,
            'table_metrics': table_metrics
        }
        
    except Exception as e:
        error_msg = f"Performance check failed: {e}"
        logger.error(error_msg)
        return {
            'error': str(e)
        }

def run_health_check(include_performance: bool = False) -> Dict:
    """Run a comprehensive health check on the database.
    
    Args:
        include_performance: Whether to include performance metrics
        
    Returns:
        Dictionary containing all health check results
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'connection': {
            'local': check_connection(local_only=True),
            'motherduck': check_connection(local_only=False)
        },
        'tables': {
            name: check_table_health(name)
            for name in TABLES
        },
        'sync': check_sync_health(),
        'schema': check_schema_consistency(),
        'size': check_database_size()
    }
    
    if include_performance:
        results['performance'] = check_query_performance()
        
    # Calculate overall health
    is_healthy = (
        results['connection']['local']
        and results['connection']['motherduck']
        and results['sync']['healthy']
        and results['schema']['consistent']
        and all(t['healthy'] for t in results['tables'].values())
    )
    
    results['healthy'] = is_healthy
    
    return results

def monitor_database(interval: int = 300, run_once: bool = False) -> None:
    """Run regular database monitoring.
    
    Args:
        interval: Monitoring interval in seconds
        run_once: Whether to run only once instead of in a loop
    """
    global _monitoring_active, _monitor_thread
    
    try:
        # Set the monitoring flag
        _monitoring_active = True
        # Set current thread as monitor thread
        _monitor_thread = threading.current_thread()
        
        logger.info(f"Starting database monitoring (interval: {interval}s)")
        
        while _monitoring_active:
            try:
                # Run health check
                health = run_health_check()
                
                # Handle issues
                if health.get('status') != 'healthy':
                    issues = health.get('issues', [])
                    for issue in issues:
                        if issue.get('severity') == 'critical':
                            logger.critical(f"Critical database issue: {issue.get('message')}")
                        elif issue.get('severity') == 'warning':
                            logger.warning(f"Database warning: {issue.get('message')}")
                            
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                
            # For single run, exit loop
            if run_once:
                break
                
            # Wait for next interval if not stopping
            if _monitoring_active:
                time.sleep(interval)
                
    except Exception as e:
        logger.error(f"Database monitoring failed: {e}")
    finally:
        _monitoring_active = False
        logger.info("Database monitoring exited")