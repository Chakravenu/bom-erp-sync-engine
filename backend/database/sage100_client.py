"""
Sage 100 ERP database client (SQLite implementation)
Manages article master data and sync history
"""
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from config import Config
from models.bom_models import BOMPart, SyncResult

logger = logging.getLogger(__name__)


class Sage100Client:
    """Client for Sage 100 ERP database (SQLite)"""
    
    def __init__(self):
        self.db_path = Config.SAGE100_DB_PATH
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """Create database schema if not exists"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Article Master Table (Sage 100 CI_Item equivalent)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS article_master (
                article_number TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                category TEXT,
                unit_of_measure TEXT DEFAULT 'EA',
                stock_quantity INTEGER DEFAULT 0,
                unit_price REAL DEFAULT 0,
                is_assembly INTEGER DEFAULT 0,
                parent_assembly TEXT,
                bom_level INTEGER DEFAULT 0,
                supplier TEXT,
                bom_version TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Sync History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_version TEXT NOT NULL,
                total_parts INTEGER,
                inserted INTEGER,
                updated INTEGER,
                errors INTEGER,
                duration_seconds REAL,
                status TEXT,
                sync_timestamp TEXT
            )
        """)
        
        # BOM Snapshots (For version comparison)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bom_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_version TEXT NOT NULL,
                article_number TEXT NOT NULL,
                description TEXT,
                unit_price REAL,
                bom_level INTEGER,
                snapshot_timestamp TEXT
            )
        """)
        
        self.conn.commit()
        logger.info(f"Sage 100 database initialized: {self.db_path}")
    
    def article_exists(self, article_number: str) -> bool:
        """Check if article exists in database"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM article_master WHERE article_number = ?",
            (article_number,)
        )
        return cursor.fetchone() is not None
    
    def insert_article(self, part: BOMPart, version: str) -> bool:
        """Insert new article into database"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO article_master (
                    article_number, description, category, unit_price,
                    is_assembly, parent_assembly, bom_level, supplier,
                    bom_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                part.part_number,
                part.description,
                part.category,
                part.unit_price,
                1 if part.is_assembly else 0,
                part.parent_assembly,
                part.bom_level,
                part.supplier,
                version,
                now,
                now
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Insert failed for {part.part_number}: {e}")
            self.conn.rollback()
            return False
    
    def update_article(self, part: BOMPart, version: str) -> bool:
        """Update existing article"""
        try:
            cursor = self.conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE article_master SET
                    description = ?,
                    category = ?,
                    unit_price = ?,
                    is_assembly = ?,
                    parent_assembly = ?,
                    bom_level = ?,
                    supplier = ?,
                    bom_version = ?,
                    updated_at = ?
                WHERE article_number = ?
            """, (
                part.description,
                part.category,
                part.unit_price,
                1 if part.is_assembly else 0,
                part.parent_assembly,
                part.bom_level,
                part.supplier,
                version,
                now,
                part.part_number
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update failed for {part.part_number}: {e}")
            self.conn.rollback()
            return False
    
    def get_all_articles(self) -> List[Dict]:
        """Fetch all articles from database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM article_master 
            ORDER BY bom_level, article_number
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_articles_by_version(self, version: str) -> List[Dict]:
        """Get articles for specific BOM version"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM article_master 
            WHERE bom_version = ?
            ORDER BY bom_level, article_number
        """, (version,))
        return [dict(row) for row in cursor.fetchall()]
    
    def save_snapshot(self, version: str):
        """Save current BOM state for version comparison"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        articles = self.get_all_articles()
        for article in articles:
            cursor.execute("""
                INSERT INTO bom_snapshots (
                    bom_version, article_number, description, 
                    unit_price, bom_level, snapshot_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                version,
                article["article_number"],
                article["description"],
                article["unit_price"],
                article["bom_level"],
                now
            ))
        
        self.conn.commit()
        logger.info(f"Saved snapshot for version {version}")
    
    def get_version_comparison(self, old_version: str, new_version: str) -> Dict:
        """Compare two BOM versions to show delta changes"""
        cursor = self.conn.cursor()
        
        # Get old version snapshot
        cursor.execute("""
            SELECT article_number, description, unit_price, bom_level
            FROM bom_snapshots WHERE bom_version = ?
        """, (old_version,))
        old_parts = {row[0]: dict(row) for row in cursor.fetchall()}
        
        # Get new version (current articles)
        cursor.execute("""
            SELECT article_number, description, unit_price, bom_level
            FROM article_master WHERE bom_version = ?
        """, (new_version,))
        new_parts = {row[0]: dict(row) for row in cursor.fetchall()}
        
        # Calculate differences
        added = []
        removed = []
        modified = []
        
        # Find added and modified
        for pn, new_data in new_parts.items():
            if pn not in old_parts:
                added.append(new_data)
            elif old_parts[pn] != new_data:
                modified.append({
                    "article_number": pn,
                    "old": old_parts[pn],
                    "new": new_data
                })
        
        # Find removed
        for pn, old_data in old_parts.items():
            if pn not in new_parts:
                removed.append(old_data)
        
        return {
            "old_version": old_version,
            "new_version": new_version,
            "added": added,
            "removed": removed,
            "modified": modified,
            "total_changes": len(added) + len(removed) + len(modified)
        }
    
    def log_sync_result(self, result: SyncResult):
        """Log synchronization result"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_history (
                bom_version, total_parts, inserted, updated, 
                errors, duration_seconds, status, sync_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.version,
            result.total_parts,
            result.inserted,
            result.updated,
            result.errors,
            result.duration_seconds,
            result.status,
            result.timestamp
        ))
        self.conn.commit()
        logger.info(f"Sync result logged for version {result.version}")
    
    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """Get recent sync history"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sync_history 
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def clear_articles(self):
        """Clear all articles (for testing)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM article_master")
        self.conn.commit()
        logger.info("All articles cleared")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()