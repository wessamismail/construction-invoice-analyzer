import sqlite3
import os
from pathlib import Path

class Database:
    def __init__(self):
        self.db_path = Path(__file__).parent / 'construction_analyzer.db'
        self.conn = None
        self.cursor = None

    def connect(self):
        """Create a database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            raise

    def disconnect(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def initialize_database(self):
        """Initialize the database with schema."""
        try:
            self.connect()
            schema_path = Path(__file__).parent / 'schema.sql'
            with open(schema_path, 'r') as schema_file:
                schema_script = schema_file.read()
                self.conn.executescript(schema_script)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            raise
        finally:
            self.disconnect()

    def execute_query(self, query, params=None):
        """Execute a query and return results."""
        try:
            self.connect()
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
            return self.cursor.fetchall()
        finally:
            self.disconnect()

    def execute_many(self, query, params_list):
        """Execute many queries at once."""
        try:
            self.connect()
            self.cursor.executemany(query, params_list)
            self.conn.commit()
        finally:
            self.disconnect()

# Create database instance
db = Database()

# Initialize database if it doesn't exist
if not os.path.exists(db.db_path):
    db.initialize_database() 