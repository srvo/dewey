def sync_to_motherduck(self):
        """Synchronize the local database to MotherDuck."""
        try:
            # Get the last sync timestamp
            last_sync = self.execute_query("""
                SELECT MAX(sync_time) FROM sync_status 
                WHERE status = 'success'
            """, local_only=True)
