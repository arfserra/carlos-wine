# services/supabase_service.py
import os
from supabase import create_client, Client
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import uuid

class SupabaseService:
    def __init__(self):
        """Initialize Supabase connection."""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        try:
            self.supabase: Client = create_client(self.url, self.key)
        except Exception as e:
            print(f"Failed to initialize Supabase client: {e}")
            raise ValueError(f"Failed to connect to Supabase: {e}")
    
    def save_storage(self, storage_data):
        """Save storage configuration to Supabase."""
        try:
            storage_id = storage_data.get("id") or f"storage_{str(uuid.uuid4())[:8]}"
            
            # Insert storage record
            storage_record = {
                "id": storage_id,
                "description": storage_data["description"],
                "zones": storage_data["zones"],
                "total_positions": storage_data["total_positions"]
            }
            
            result = self.supabase.table("storage").insert(storage_record).execute()
            
            # Create positions
            positions_data = []
            for zone in storage_data["zones"]:
                for position in zone["positions"]:
                    positions_data.append({
                        "id": position.get("id") or f"pos_{str(uuid.uuid4())[:8]}",
                        "storage_id": storage_id,
                        "zone": zone["name"],
                        "identifier": position["identifier"],
                        "is_occupied": False
                    })
            
            if positions_data:
                self.supabase.table("positions").insert(positions_data).execute()
            
            return storage_id
        except Exception as e:
            print(f"Error saving storage: {e}")
            return None
    
    def add_wine(self, wine_data):
        """Add a wine to the collection."""
        try:
            wine_id = wine_data.get("id") or f"wine_{str(uuid.uuid4())[:8]}"
            
            # Update position to occupied if position_id provided
            if wine_data.get("position_id"):
                self.supabase.table("positions").update({
                    "is_occupied": True,
                    "wine_id": wine_id
                }).eq("id", wine_data["position_id"]).execute()
            
            # Add wine
            wine_record = {
                "id": wine_id,
                "name": wine_data["name"],
                "description": wine_data["description"],
                "position_id": wine_data.get("position_id"),
                "added_date": datetime.now().isoformat()
            }
            
            result = self.supabase.table("wines").insert(wine_record).execute()
            return wine_id
        except Exception as e:
            print(f"Error adding wine: {e}")
            return None
    
    def mark_wine_consumed(self, wine_id):
        """Mark a wine as consumed and free up its position."""
        try:
            # Get wine's current position
            wine_result = self.supabase.table("wines").select("position_id").eq("id", wine_id).execute()
            
            if not wine_result.data:
                return False
            
            position_id = wine_result.data[0].get("position_id")
            
            # Update wine
            self.supabase.table("wines").update({
                "consumed": True,
                "consumed_date": datetime.now().isoformat(),
                "position_id": None
            }).eq("id", wine_id).execute()
            
            # Free up position
            if position_id:
                self.supabase.table("positions").update({
                    "is_occupied": False,
                    "wine_id": None
                }).eq("id", position_id).execute()
            
            return True
        except Exception as e:
            print(f"Error marking wine consumed: {e}")
            return False
    
    def get_wines(self, include_consumed=False):
        """Get all wines in the collection."""
        try:
            query = self.supabase.table("wines").select("""
                *,
                positions!inner(identifier, zone)
            """)
            
            if not include_consumed:
                query = query.eq("consumed", False)
            
            result = query.execute()
            
            wines = []
            for wine in result.data:
                wine_dict = dict(wine)
                # Flatten position data
                if wine_dict.get("positions"):
                    wine_dict["position_identifier"] = wine_dict["positions"]["identifier"]
                    wine_dict["position_zone"] = wine_dict["positions"]["zone"]
                    del wine_dict["positions"]
                wines.append(wine_dict)
            
            return wines
        except Exception as e:
            print(f"Error getting wines: {e}")
            return []
    
    def get_wine_by_id(self, wine_id):
        """Get a specific wine by ID."""
        try:
            result = self.supabase.table("wines").select("*").eq("id", wine_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting wine by ID: {e}")
            return None
    
    def get_available_positions(self):
        """Get all available positions."""
        try:
            result = self.supabase.table("positions").select("*").eq("is_occupied", False).execute()
            return result.data
        except Exception as e:
            print(f"Error getting available positions: {e}")
            return []
    
    def get_all_positions(self):
        """Get all positions (available and occupied)."""
        try:
            result = self.supabase.table("positions").select("*").execute()
            return result.data
        except Exception as e:
            print(f"Error getting all positions: {e}")
            return []
    
    def has_storage(self):
        """Check if any storage has been configured."""
        try:
            result = self.supabase.table("storage").select("id").execute()
            return len(result.data) > 0
        except Exception as e:
            print(f"Error checking storage: {e}")
            return False
    
    def move_wine_to_position(self, wine_id, new_position_id):
        """Move a wine to a new position."""
        try:
            # Get current position
            wine_result = self.supabase.table("wines").select("position_id").eq("id", wine_id).execute()
            
            if not wine_result.data:
                return False
            
            current_position_id = wine_result.data[0].get("position_id")
            
            # Free up current position if it exists
            if current_position_id:
                self.supabase.table("positions").update({
                    "is_occupied": False,
                    "wine_id": None
                }).eq("id", current_position_id).execute()
            
            # Check if new position is occupied
            position_result = self.supabase.table("positions").select("is_occupied, wine_id").eq("id", new_position_id).execute()
            
            if not position_result.data:
                return False
            
            # If position is occupied, swap wines
            if position_result.data[0]["is_occupied"]:
                occupied_wine_id = position_result.data[0]["wine_id"]
                
                # Move occupied wine to old position
                if current_position_id:
                    self.supabase.table("wines").update({
                        "position_id": current_position_id
                    }).eq("id", occupied_wine_id).execute()
                    
                    self.supabase.table("positions").update({
                        "is_occupied": True,
                        "wine_id": occupied_wine_id
                    }).eq("id", current_position_id).execute()
            
            # Move wine to new position
            self.supabase.table("wines").update({
                "position_id": new_position_id
            }).eq("id", wine_id).execute()
            
            self.supabase.table("positions").update({
                "is_occupied": True,
                "wine_id": wine_id
            }).eq("id", new_position_id).execute()
            
            return True
        except Exception as e:
            print(f"Error moving wine: {e}")
            return False
