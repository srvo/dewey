import logging

logger = logging.getLogger(__name__)

def sync_to_motherduck(self):
        """Synchronize the local database to MotherDuck."""
        try:
            # Get the last sync timestamp
            last_sync = self.execute_query("""
                SELECT MAX(sync_time) FROM sync_status 
                WHERE status = 'success'
            """, local_only=True)
        except Exception as e:
            logger.error(f"Error getting last sync time: {e}")
            return None
