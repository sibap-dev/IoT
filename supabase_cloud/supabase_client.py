import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_supabase_client = None

def init_supabase():
    """Initialize official Supabase Python client if credentials exist."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not configured. Falling back to local/rule-based mode.")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Successfully initialized Supabase Client.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        return None

def get_supabase():
    """Retrieve existing Supabase Client or attempt initialization."""
    global _supabase_client
    if _supabase_client is None:
        return init_supabase()
    return _supabase_client
