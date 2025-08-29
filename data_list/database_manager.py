#!/usr/bin/env python3
"""
Database manager for OFAC sanctions list data
"""

import sqlite3
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OFACDatabaseManager:
    """Manage SQLite database for OFAC sanctions data"""
    
    def __init__(self, db_path: str = "data_list/ofac_sanctions.db"):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        logger.info(f"Connected to database: {self.db_path}")
        
    def disconnect(self):
        """Disconnect from the database"""
        if self.conn:
            self.conn.close()
            logger.info("Disconnected from database")
            
    def create_schema(self):
        """Create database schema for OFAC data"""
        logger.info("Creating database schema...")
        
        # Main sanctions table - simplified structure
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sanctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE,
                name TEXT,
                details TEXT,  -- All other information as a single string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for common search fields
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_uid ON sanctions(uid)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON sanctions(name)')
        
        # Import history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_file TEXT,
                records_imported INTEGER,
                records_updated INTEGER,
                records_failed INTEGER,
                status TEXT,
                error_message TEXT
            )
        ''')
        
        self.conn.commit()
        logger.info("Database schema created successfully")
        
    def import_csv(self, csv_path: str, update_existing: bool = True) -> Dict[str, int]:
        """Import CSV data into the database
        
        Args:
            csv_path: Path to CSV file
            update_existing: Whether to update existing records
            
        Returns:
            Dictionary with import statistics
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
        logger.info(f"Importing CSV data from: {csv_path}")
        
        stats = {
            'total': 0,
            'imported': 0,
            'updated': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    stats['total'] += 1
                    
                    try:
                        # Check if record exists
                        self.cursor.execute('SELECT id FROM sanctions WHERE uid = ?', (row['uid'],))
                        existing = self.cursor.fetchone()
                        
                        # Prepare name and details
                        name = row.get('primary_name', '') or row.get('name', '')
                        
                        # Build details string from all other fields
                        details_parts = []
                        if row.get('party_type'):
                            details_parts.append(f"Type: {row['party_type']}")
                        if row.get('aliases'):
                            details_parts.append(f"Aliases: {row['aliases']}")
                        if row.get('dates_of_birth'):
                            details_parts.append(f"DOB: {row['dates_of_birth']}")
                        if row.get('places_of_birth'):
                            details_parts.append(f"POB: {row['places_of_birth']}")
                        if row.get('nationalities'):
                            details_parts.append(f"Nationality: {row['nationalities']}")
                        if row.get('addresses'):
                            details_parts.append(f"Address: {row['addresses']}")
                        if row.get('programs'):
                            details_parts.append(f"Programs: {row['programs']}")
                        if row.get('remarks'):
                            details_parts.append(f"Remarks: {row['remarks']}")
                        
                        details = ' | '.join(details_parts)
                        
                        if existing:
                            if update_existing:
                                # Update existing record
                                self.cursor.execute('''
                                    UPDATE sanctions SET
                                        name = ?,
                                        details = ?,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE uid = ?
                                ''', (name, details, row['uid']))
                                stats['updated'] += 1
                            else:
                                stats['skipped'] += 1
                        else:
                            # Insert new record
                            self.cursor.execute('''
                                INSERT INTO sanctions (uid, name, details)
                                VALUES (?, ?, ?)
                            ''', (row.get('uid', ''), name, details))
                            stats['imported'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing row {stats['total']}: {e}")
                        stats['failed'] += 1
                        
                # Commit the transaction
                self.conn.commit()
                
                # Record import history
                self.cursor.execute('''
                    INSERT INTO import_history (
                        source_file, records_imported, records_updated,
                        records_failed, status
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(csv_file.name),
                    stats['imported'],
                    stats['updated'],
                    stats['failed'],
                    'SUCCESS'
                ))
                self.conn.commit()
                
                logger.info(f"Import completed: {stats}")
                
        except Exception as e:
            logger.error(f"Import failed: {e}")
            self.conn.rollback()
            
            # Record failed import
            self.cursor.execute('''
                INSERT INTO import_history (
                    source_file, records_imported, records_updated,
                    records_failed, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(csv_file.name),
                stats['imported'],
                stats['updated'],
                stats['failed'],
                'FAILED',
                str(e)
            ))
            self.conn.commit()
            raise
            
        return stats
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for sanctions entries
        
        Args:
            query: Search query (searches in names)
            limit: Maximum number of results
            
        Returns:
            List of matching records
        """
        search_pattern = f'%{query}%'
        
        self.cursor.execute('''
            SELECT * FROM sanctions
            WHERE name LIKE ? OR details LIKE ?
            LIMIT ?
        ''', (search_pattern, search_pattern, limit))
        
        columns = [desc[0] for desc in self.cursor.description]
        results = []
        
        for row in self.cursor.fetchall():
            record = dict(zip(columns, row))
            results.append(record)
            
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        stats = {}
        
        # Total records
        self.cursor.execute('SELECT COUNT(*) FROM sanctions')
        stats['total_records'] = self.cursor.fetchone()[0]
        
        # Count total records only
        # (removed by_type query since we don't have that field anymore)
        
        # Recent imports
        self.cursor.execute('''
            SELECT * FROM import_history
            ORDER BY import_date DESC
            LIMIT 5
        ''')
        columns = [desc[0] for desc in self.cursor.description]
        stats['recent_imports'] = [
            dict(zip(columns, row)) for row in self.cursor.fetchall()
        ]
        
        return stats


def main():
    """Main function to manage database"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage OFAC sanctions database")
    parser.add_argument(
        "action",
        choices=["create", "import", "search", "stats"],
        help="Action to perform"
    )
    parser.add_argument(
        "--csv",
        default="data_list/ofac_consolidated.csv",
        help="CSV file to import (for import action)"
    )
    parser.add_argument(
        "--db",
        default="data_list/ofac_sanctions.db",
        help="Database file path"
    )
    parser.add_argument(
        "--query",
        help="Search query (for search action)"
    )
    args = parser.parse_args()
    
    db = OFACDatabaseManager(args.db)
    
    try:
        db.connect()
        
        if args.action == "create":
            db.create_schema()
            logger.info("Database schema created successfully")
            
        elif args.action == "import":
            db.create_schema()  # Ensure schema exists
            stats = db.import_csv(args.csv)
            logger.info(f"Import complete: {stats}")
            
        elif args.action == "search":
            if not args.query:
                logger.error("Search query required")
                return 1
            results = db.search(args.query)
            logger.info(f"Found {len(results)} results")
            for r in results:
                print(f"- {r['uid']}: {r['name']}")
                
        elif args.action == "stats":
            stats = db.get_statistics()
            print("\n=== Database Statistics ===")
            print(f"Total Records: {stats['total_records']}")
            print("\nRecent Imports:")
            for imp in stats['recent_imports']:
                print(f"  - {imp['import_date']}: {imp['source_file']} ({imp['status']})")
                print(f"    Imported: {imp['records_imported']}, Updated: {imp['records_updated']}")
                
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return 1
    finally:
        db.disconnect()
    
    return 0


if __name__ == "__main__":
    exit(main())