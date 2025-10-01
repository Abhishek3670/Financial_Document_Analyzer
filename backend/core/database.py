"""
Database connection and session management for Financial Document Analyzer
"""
import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import sqlite3

from backend.models.models import Base, User, Document, Analysis, AnalysisHistory

# Setup logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or self._get_database_url()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
        
    def _get_database_url(self) -> str:
        """Get database URL from environment or use default SQLite"""
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
            
        # Default to SQLite in the project directory
        db_path = os.path.join(os.getcwd(), 'financial_analyzer.db')
        return f"sqlite:///{db_path}"
    
    def _initialize_engine(self):
        """Initialize database engine with appropriate settings"""
        if self.database_url.startswith('sqlite'):
            # SQLite-specific configuration
            self.engine = create_engine(
                self.database_url,
                connect_args={
                    "check_same_thread": False,  # Allow multiple threads
                    "timeout": 20,  # 20 second timeout
                },
                poolclass=StaticPool,  # Use StaticPool for SQLite
                echo=os.getenv('DATABASE_DEBUG', '').lower() == 'true'  # Log SQL queries if DEBUG is true
            )
            
            # Enable WAL mode for better concurrent access
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                if isinstance(dbapi_connection, sqlite3.Connection):
                    cursor = dbapi_connection.cursor()
                    # Enable WAL mode for better concurrency
                    cursor.execute("PRAGMA journal_mode=WAL")
                    # Enable foreign key constraints
                    cursor.execute("PRAGMA foreign_keys=ON")
                    # Set cache size (negative value = KB, positive = pages)
                    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                    cursor.close()
                    
        else:
            # PostgreSQL or other database configuration
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=os.getenv('DATABASE_DEBUG', '').lower() == 'true'
            )
        
        # Create session factory
        self.SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        )
        
        logger.info(f"Database engine initialized with URL: {self._mask_db_url(self.database_url)}")
    
    def _mask_db_url(self, url: str) -> str:
        """Mask sensitive information in database URL for logging"""
        if '://' in url:
            protocol, rest = url.split('://', 1)
            if '@' in rest:
                # Has credentials
                creds, host_part = rest.split('@', 1)
                return f"{protocol}://***:***@{host_part}"
            else:
                return url
        return url
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator:
        """Provide a transactional scope around a series of operations"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            with self.session_scope() as session:
                # Simple query to test connection
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """Get database information for monitoring"""
        try:
            with self.session_scope() as session:
                if self.database_url.startswith('sqlite'):
                    # SQLite-specific info
                    result = session.execute(text("PRAGMA database_list")).fetchall()
                    db_file = result[0][2] if result else "memory"
                    
                    # Get file size
                    db_size = 0
                    if db_file and os.path.exists(db_file):
                        db_size = os.path.getsize(db_file)
                    
                    return {
                        "type": "SQLite",
                        "file": db_file,
                        "size_bytes": db_size,
                        "size_mb": round(db_size / 1024 / 1024, 2)
                    }
                else:
                    # Generic database info
                    return {
                        "type": "Other",
                        "url": self._mask_db_url(self.database_url)
                    }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}

# Global database manager instance
db_manager = None

def init_database(database_url: str = None) -> DatabaseManager:
    """Initialize the global database manager"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager

def get_db_session():
    """Dependency function for FastAPI to get database session"""
    if not db_manager:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

def get_database_manager() -> DatabaseManager:
    """Get the global database manager"""
    if not db_manager:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return db_manager

# Utility functions for common operations
def create_user_session(ip_address: str = None, user_agent: str = None) -> User:
    """Create a new user session"""
    with db_manager.session_scope() as session:
        user = User(ip_address=ip_address, user_agent=user_agent)
        session.add(user)
        session.flush()  # Get the ID without committing
        return user

def get_user_by_session_id(session_id: str) -> User:
    """Get user by session ID"""
    with db_manager.session_scope() as session:
        return session.query(User).filter(User.session_id == session_id).first()

def update_user_activity(user_id: str):
    """Update user's last activity timestamp"""
    with db_manager.session_scope() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.last_activity = datetime.utcnow()
            session.flush()

# Database initialization check
def ensure_database_initialized():
    """Ensure database is initialized, initialize if not"""
    global db_manager
    if not db_manager:
        logger.info("Database not initialized, initializing with default settings...")
        init_database()
    return db_manager
