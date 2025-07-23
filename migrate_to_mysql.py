
#!/usr/bin/env python3
"""
Migration script to transfer data from debate_data.json to MySQL database
Run this once after setting up MySQL to migrate existing data
"""

import json
import os
from database import db_manager

def migrate_json_to_mysql():
    """Migrate existing JSON data to MySQL database"""
    
    # Check if JSON file exists
    if not os.path.exists('debate_data.json'):
        print("No debate_data.json file found. Starting with fresh database.")
        return
    
    try:
        # Load JSON data
        with open('debate_data.json', 'r') as f:
            json_data = json.load(f)
        
        print("Loading JSON data...")
        
        # Initialize database
        db_manager.init_database()
        print("Database initialized.")
        
        # Save JSON data to MySQL
        db_manager.save_data(json_data)
        print("Data migrated successfully!")
        
        # Backup the JSON file
        import shutil
        shutil.copy('debate_data.json', 'debate_data.json.backup')
        print("JSON file backed up as debate_data.json.backup")
        
        # Verify migration
        migrated_data = db_manager.load_data()
        print(f"Verification: Found {len(migrated_data['users'])} users, {len(migrated_data['players'])} players, {len(migrated_data['teams'])} teams")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("Starting migration from JSON to MySQL...")
    success = migrate_json_to_mysql()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. Please check the error messages above.")
