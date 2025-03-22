# services/storage_service.py
from database import Database

class StorageService:
    def __init__(self):
        """Initialize storage service with database connection."""
        self.db = Database()
    
    def create_storage(self, storage_data):
        """Create a new storage configuration."""
        return self.db.save_storage(storage_data)
    
    def get_available_positions(self):
        """Get all available positions in the storage."""
        return self.db.get_available_positions()
    
    def has_storage(self):
        """Check if any storage has been configured."""
        return self.db.has_storage()