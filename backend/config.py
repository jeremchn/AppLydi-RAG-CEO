import os
import yaml
from typing import Dict, Any

class Config:
    """Configuration management"""
    
    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            "database": {
                "url": os.getenv("DATABASE_URL", "postgresql://applydiuser:applydipass@localhost/applydidb"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10"))
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                "chat_model": os.getenv("OPENAI_CHAT_MODEL", "gpt-4")
            },
            "jwt": {
                "secret_key": os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
                "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
                "expires_hours": int(os.getenv("JWT_EXPIRES_HOURS", "24"))
            },
            "google_cloud": {
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "region": os.getenv("GOOGLE_CLOUD_REGION", "europe-west1")
            },
            "app": {
                "title": "AppLydi API",
                "version": "1.0.0",
                "allowed_origins": os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
                "max_file_size": int(os.getenv("MAX_FILE_SIZE", "10485760")),  # 10MB
                "supported_formats": ["pdf", "txt", "docx"]
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            value = value.get(k, default)
            if value is None:
                return default
        return value

# Global config instance
config = Config()
