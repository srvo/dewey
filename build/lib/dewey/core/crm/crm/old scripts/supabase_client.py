from supabase import create_client, Client
from typing import Optional

class SupabaseClient:
    def __init__(self):
        self.url: str = "https://fjzxtsewrykbrfjzatti.supabase.co"
        self.key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZqenh0c2V3cnlrYnJmanphdHRpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMTc0MTQ4NSwiZXhwIjoyMDQ3MzE3NDg1fQ.EwiwOABEcMLmY_gLEeeMbNWTWeJf-FhARjR1OHANO1Q"
        
    def get_client(self) -> Client:
        """Get Supabase client with service role access"""
        return create_client(self.url, self.key)