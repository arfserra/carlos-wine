import sqlite3
import json
from datetime import datetime
import uuid

class Database:
    def __init__(self, db_path="wine_collection.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = None
        self.create_tables()
    
    def get_connection(self):
        """Get a database connection, creating one if necessary."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def create_tables(self):
        """Create necessary tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Storage table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS storage (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            zones TEXT NOT NULL,  -- JSON string
            total_positions INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Positions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            storage_id TEXT NOT NULL,
            zone TEXT NOT NULL,
            identifier TEXT NOT NULL,
            is_occupied INTEGER DEFAULT 0,
            wine_id TEXT,
            FOREIGN KEY (storage_id) REFERENCES storage(id)
        )
        ''')
        
        # Wines table (simplified structure)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wines (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,  -- Rich description containing all details
            position_id TEXT,
            added_date TEXT NOT NULL,
            consumed INTEGER DEFAULT 0,
            consumed_date TEXT,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        )
        ''')
        
        conn.commit()
    
    def save_storage(self, storage_data):
        """Save storage configuration to database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        storage_id = storage_data.get("id") or f"storage_{str(uuid.uuid4())[:8]}"
        zones_json = json.dumps(storage_data["zones"])
        
        cursor.execute(
            '''
            INSERT INTO storage (id, description, zones, total_positions, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                storage_id,
                storage_data["description"],
                zones_json,
                storage_data["total_positions"],
                datetime.now().isoformat()
            )
        )
        
        # Create positions based on storage configuration
        for zone in storage_data["zones"]:
            for position in zone["positions"]:
                cursor.execute(
                    '''
                    INSERT INTO positions (id, storage_id, zone, identifier, is_occupied)
                    VALUES (?, ?, ?, ?, 0)
                    ''',
                    (
                        position.get("id") or f"pos_{str(uuid.uuid4())[:8]}",
                        storage_id,
                        zone["name"],
                        position["identifier"]
                    )
                )
        
        conn.commit()
        return storage_id
    
    def add_wine(self, wine_data):
        """Add a wine to the collection and assign to a position."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        wine_id = wine_data.get("id") or f"wine_{str(uuid.uuid4())[:8]}"
        
        # Update position to occupied if position_id provided
        if wine_data.get("position_id"):
            cursor.execute(
                '''
                UPDATE positions
                SET is_occupied = 1, wine_id = ?
                WHERE id = ?
                ''',
                (wine_id, wine_data["position_id"])
            )
        
        # Add wine to database
        cursor.execute(
            '''
            INSERT INTO wines (id, name, description, position_id, added_date, consumed)
            VALUES (?, ?, ?, ?, ?, 0)
            ''',
            (
                wine_id,
                wine_data["name"],
                wine_data["description"],
                wine_data.get("position_id"),
                datetime.now().isoformat()
            )
        )
        
        conn.commit()
        return wine_id
    
    def mark_wine_consumed(self, wine_id):
        """Mark a wine as consumed and free up its position."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get position ID
        cursor.execute("SELECT position_id FROM wines WHERE id = ?", (wine_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        position_id = result["position_id"]
        
        # Update wine
        cursor.execute(
            '''
            UPDATE wines
            SET consumed = 1, consumed_date = ?, position_id = NULL
            WHERE id = ?
            ''',
            (datetime.now().isoformat(), wine_id)
        )
        
        # Free up position
        if position_id:
            cursor.execute(
                '''
                UPDATE positions
                SET is_occupied = 0, wine_id = NULL
                WHERE id = ?
                ''',
                (position_id,)
            )
        
        conn.commit()
        return True
    
    def get_wines(self, include_consumed=False):
        """Get all wines in the collection."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM wines"
        if not include_consumed:
            query += " WHERE consumed = 0"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_wine_by_id(self, wine_id):
        """Get a specific wine by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM wines WHERE id = ?", (wine_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None

    def get_available_positions(self):
        """Get all available positions."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT p.*, s.zones
            FROM positions p
            JOIN storage s ON p.storage_id = s.id
            WHERE p.is_occupied = 0
            '''
        )
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            position = dict(row)
            # Add zone details from the zones JSON
            zones = json.loads(position.pop("zones"))
            for zone in zones:
                if zone["name"] == position["zone"]:
                    position["zone_details"] = zone
                    break
            results.append(position)
        
        return results
    
    def has_storage(self):
        """Check if any storage has been configured."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM storage")
        result = cursor.fetchone()
        
        return result["count"] > 0