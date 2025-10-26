import os
import streamlit as st

class Database:
    def __init__(self, db_path="wine_collection.db"):
        """Initialize database connection - requires Supabase for persistence."""
        try:
            # Import here to avoid circular import
            from services.supabase_service import SupabaseService
            self.supabase = SupabaseService()
            self.use_supabase = True
            print("Successfully connected to Supabase for persistent storage")
        except Exception as e:
            print(f"Failed to connect to Supabase: {e}")
            raise ValueError(f"Unable to connect to Supabase database. Please check your credentials and try again. Error: {e}")
    
    def get_connection(self):
        """Get a database connection."""
        return self.supabase
    
    def save_storage(self, storage_data):
        """Save storage configuration to database."""
        return self.supabase.save_storage(storage_data)
    
    def add_wine(self, wine_data):
        """Add a wine to the collection and assign to a position."""
        return self.supabase.add_wine(wine_data)
    
    def mark_wine_consumed(self, wine_id):
        """Mark a wine as consumed and free up its position."""
        return self.supabase.mark_wine_consumed(wine_id)
    
    def get_wines(self, include_consumed=False):
        """Get all wines in the collection."""
        return self.supabase.get_wines(include_consumed)
    
    def get_wine_by_id(self, wine_id):
        """Get a specific wine by ID."""
        return self.supabase.get_wine_by_id(wine_id)
    
    def get_available_positions(self):
        """Get all available positions."""
        return self.supabase.get_available_positions()
    
    def has_storage(self):
        """Check if any storage has been configured."""
        return self.supabase.has_storage()
    
    def get_all_positions(self):
        """Get all positions (available and occupied)."""
        return self.supabase.get_all_positions()
    
    def move_wine_to_position(self, wine_id, new_position_id):
        """Move a wine to a new position."""
        return self.supabase.move_wine_to_position(wine_id, new_position_id)
    
    def delete_wine(self, wine_id):
        """Delete a wine from the collection permanently."""
        return self.supabase.delete_wine(wine_id)