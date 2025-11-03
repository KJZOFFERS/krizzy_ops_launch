# config.py
import os
from typing import List, Optional

class Config:
    """Centralized configuration from environment variables"""
    
    # Discord webhooks
    DISCORD_WEBHOOK_OPS: Optional[List[str]] = None
    DISCORD_WEBHOOK_ERRORS: Optional[List[str]] = None
    
    # Airtable
    AIRTABLE_API_KEY: Optional[str] = None
    AIRTABLE_BASE_ID: Optional[str] = None
    
    # N8N
    N8N_REI_URL: Optional[str] = None
    N8N_GOVCON_URL: Optional[str] = None
    N8N_API_KEY: Optional[str] = None
    
    def __init__(self):
        # Discord - support comma-separated or single webhook
        ops_raw = os.getenv("DISCORD_WEBHOOK_OPS", "")
        if ops_raw:
            self.DISCORD_WEBHOOK_OPS = [w.strip() for w in ops_raw.split(",") if w.strip()]
        
        err_raw = os.getenv("DISCORD_WEBHOOK_ERRORS", "")
        if err_raw:
            self.DISCORD_WEBHOOK_ERRORS = [w.strip() for w in err_raw.split(",") if w.strip()]
        
        # Airtable
        self.AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
        self.AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
        
        # N8N
        self.N8N_REI_URL = os.getenv("N8N_REI_URL")
        self.N8N_GOVCON_URL = os.getenv("N8N_GOVCON_URL")
        self.N8N_API_KEY = os.getenv("N8N_API_KEY")

# Global config instance
CFG = Config()
