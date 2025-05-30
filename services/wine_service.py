# services/wine_service.py
from database import Database

class WineService:
    def __init__(self):
        """Initialize wine service with database connection."""
        self.db = Database()
    
    def add_wine(self, wine_data):
        """Add a wine to the collection."""
        return self.db.add_wine(wine_data)
    
    def mark_wine_consumed(self, wine_id):
        """Mark a wine as consumed and free up its position."""
        return self.db.mark_wine_consumed(wine_id)
    
    def get_wines(self, include_consumed=False):
        """Get all wines in the collection."""
        return self.db.get_wines(include_consumed)
    
    def get_wine_by_id(self, wine_id):
        """Get a specific wine by ID."""
        return self.db.get_wine_by_id(wine_id)