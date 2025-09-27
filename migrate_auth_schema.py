#!/usr/bin/env python3
"""
Migration script to add authentication columns to existing database
"""
import sqlite3
import os
from database import init_database, get_database_manager
from models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migrate database schema to support authentication"""
    db_path = 'financial_analyzer.db'
    
    # Backup database first
    backup_path = f"{db_path}.backup_before_auth_migration"
    if os.path.exists(db_path):
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if we need to migrate
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'email' in columns:
            logger.info("Database already has authentication columns")
            return True
        
        logger.info("Adding authentication columns to users table...")
        
        # Add new columns for authentication
        migration_queries = [
            "ALTER TABLE users ADD COLUMN email VARCHAR",
            "ALTER TABLE users ADD COLUMN username VARCHAR", 
            "ALTER TABLE users ADD COLUMN password_hash VARCHAR",
            "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
            "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN first_name VARCHAR",
            "ALTER TABLE users ADD COLUMN last_name VARCHAR",
            "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_login DATETIME",
            "ALTER TABLE users ADD COLUMN password_reset_token VARCHAR",
            "ALTER TABLE users ADD COLUMN password_reset_expires DATETIME"
        ]
        
        for query in migration_queries:
            try:
                cursor.execute(query)
                logger.info(f"✅ Executed: {query}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"⚠️  Column already exists: {query}")
                else:
                    raise
        
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Create indexes for performance
        index_queries = [
            "CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)"
        ]
        
        for query in index_queries:
            cursor.execute(query)
            logger.info(f"✅ Created index: {query}")
        
        conn.commit()
        
        # Verify migration
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        logger.info("✅ Final users table schema:")
        for col in columns:
            logger.info(f"  {col[1]} {col[2]} (nullable: {not col[3]}, default: {col[4]})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 Starting database migration for authentication...")
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("✅ Database is now ready for authentication!")
        
        # Test that we can now initialize with new schema
        try:
            db_manager = init_database()
            engine = db_manager.engine
            Base.metadata.create_all(bind=engine)
            print("✅ SQLAlchemy models work with migrated schema")
        except Exception as e:
            print(f"❌ Error with SQLAlchemy: {e}")
    else:
        print("\n❌ Migration failed! Check the logs above.")
