import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Supabase (S1000D Source System)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # Sage 100 (SQLite for demo)
    SAGE100_DB_PATH = os.getenv("SAGE100_DB_PATH", "./sage100_avilus.db")
    
    # API Server
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def validate():
        """Ensure required credentials are present"""
        missing = []
        if not Config.SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not Config.SUPABASE_KEY:
            missing.append("SUPABASE_KEY")
        
        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True