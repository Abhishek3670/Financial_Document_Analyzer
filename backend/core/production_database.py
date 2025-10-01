"""
Production Database Setup and Management
Handles database initialization, migrations, and production configurations
"""
import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from datetime import datetime
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionDatabase:
    """Production database management"""
    
    def __init__(self):
        self.current_db_url = os.getenv("DATABASE_URL", "sqlite:///./financial_analyzer.db")
        self.production_db_url = os.getenv("PRODUCTION_DATABASE_URL", "sqlite:///./production_financial_analyzer.db")
        self.backup_dir = Path("./database_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self, db_path: str = None) -> str:
        """Create a backup of the current database"""
        try:
            if db_path is None:
                # Extract path from current DATABASE_URL
                if self.current_db_url.startswith("sqlite:///"):
                    db_path = self.current_db_url.replace("sqlite:///", "")
                else:
                    raise ValueError("Backup only supported for SQLite databases")
            
            if not os.path.exists(db_path):
                logger.warning(f"Database file not found: {db_path}")
                return None
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}_{os.path.basename(db_path)}"
            backup_path = self.backup_dir / backup_filename
            
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Database backup created: {backup_path}")
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            raise
    
    def create_production_config(self) -> dict:
        """Generate production database configuration"""
        config = {
            "sqlite": {
                "url": "sqlite:///./production_financial_analyzer.db",
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "echo": False
            },
            "postgresql": {
                "url": "postgresql://username:password@localhost:5432/financial_analyzer_prod",
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "echo": False
            },
            "mysql": {
                "url": "mysql+pymysql://username:password@localhost:3306/financial_analyzer_prod",
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "echo": False
            }
        }
        return config
    
    def create_production_env(self):
        """Create production environment file"""
        prod_env_content = f"""# Production Database Configuration
# Generated on {datetime.now().isoformat()}

# Choose your database type and configure accordingly
# For SQLite (simple, single-file database)
DATABASE_URL=sqlite:///./production_financial_analyzer.db
DATABASE_DEBUG=false

# For PostgreSQL (recommended for production)
# DATABASE_URL=postgresql://username:password@localhost:5432/financial_analyzer_prod
# DATABASE_DEBUG=false

# For MySQL/MariaDB
# DATABASE_URL=mysql+pymysql://username:password@localhost:3306/financial_analyzer_prod
# DATABASE_DEBUG=false

# Database Connection Pool Settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# File Storage Configuration (Production)
KEEP_UPLOADED_FILES=true
MAX_STORED_FILES_PER_USER=50
FILE_CLEANUP_DAYS=30

# Security Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# LLM Configuration
MODEL=nvidia_nim/openai/gpt-oss-20b
NVIDIA_NIM_API_KEY=your-nvidia-nim-api-key
OPENAI_API_KEY=your-openai-api-key
SERPER_API_KEY=your-serper-api-key

# Observability
LLM_OBSERVABILITY_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Redis Configuration
REDIS_CACHE_ENABLED=true
REDIS_URL=redis://localhost:6379/0
REDIS_DEFAULT_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/financial_analyzer.log
"""
        
        with open(".env.production", "w") as f:
            f.write(prod_env_content)
        
        logger.info("✅ Production environment file created: .env.production")
    
    def create_database_init_script(self):
        """Create database initialization script"""
        script_content = '''#!/bin/bash
# Database Initialization Script for Production
# Run this script to set up the production database

echo "🗄️  Financial Analyzer - Production Database Setup"
echo "=================================================="

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production file not found!"
    echo "Please run: python production_database.py create-env"
    exit 1
fi

# Source production environment
export $(cat .env.production | grep -v '^#' | xargs)

echo "📋 Database Configuration:"
echo "   URL: $DATABASE_URL"
echo "   Debug: $DATABASE_DEBUG"
echo ""

# Create backup of existing database if it exists
if [ -f "financial_analyzer.db" ]; then
    echo "💾 Creating backup of existing database..."
    python -c "from production_database import ProductionDatabase; ProductionDatabase().create_backup()"
fi

# Initialize database
echo "🔧 Initializing production database..."
python -c "
from backend.core.database import init_database
from backend.models.models import *
import os

# Set production environment
os.environ['DATABASE_URL'] = '$DATABASE_URL'
os.environ['DATABASE_DEBUG'] = '$DATABASE_DEBUG'

# Initialize database
print('Creating database tables...')
init_database()
print('✅ Database initialized successfully')
"

# Run migrations if needed
echo "🔄 Running database migrations..."
python migrate_auth_schema.py

echo ""
echo "✅ Production database setup completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Update your .env.production file with actual credentials"
echo "   2. Test the database connection"
echo "   3. Start the application with production settings"
echo ""
echo "🚀 To start with production settings:"
echo "   cp .env.production .env"
echo "   python main.py"
'''
        
        with open("init_production_db.sh", "w") as f:
            f.write(script_content)
        
        os.chmod("init_production_db.sh", 0o755)
        logger.info("✅ Database initialization script created: init_production_db.sh")
    
    def create_docker_compose(self):
        """Create docker-compose file for production services"""
        docker_compose_content = '''version: '3.8'

services:
  # PostgreSQL Database (recommended for production)
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: financial_analyzer_prod
      POSTGRES_USER: financial_user
      POSTGRES_PASSWORD: secure_password_change_this
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database_backups:/backups
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U financial_user -d financial_analyzer_prod"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Application (uncomment when ready for containerization)
  # app:
  #   build: .
  #   environment:
  #     - DATABASE_URL=postgresql://financial_user:secure_password_change_this@postgres:5432/financial_analyzer_prod
  #     - REDIS_URL=redis://redis:6379/0
  #   depends_on:
  #     postgres:
  #       condition: service_healthy
  #     redis:
  #       condition: service_healthy
  #   ports:
  #     - "8000:8000"
  #   volumes:
  #     - ./storage:/app/storage
  #     - ./logs:/app/logs
  #   restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
'''
        
        with open("docker-compose.prod.yml", "w") as f:
            f.write(docker_compose_content)
        
        logger.info("✅ Production Docker Compose file created: docker-compose.prod.yml")
    
    def create_migration_script(self):
        """Create database migration helper script"""
        migration_content = '''#!/usr/bin/env python3
"""
Database Migration Script
Handles schema changes and data migrations
"""
import os
import sys
from sqlalchemy import create_engine, text
from backend.core.database import get_database_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration(migration_sql: str, description: str):
    """Run a migration SQL statement"""
    try:
        db_manager = get_database_manager()
        engine = db_manager.engine
        
        logger.info(f"Running migration: {description}")
        with engine.begin() as conn:
            conn.execute(text(migration_sql))
        
        logger.info(f"✅ Migration completed: {description}")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {description} - {e}")
        raise

def migrate_to_v2():
    """Example migration to version 2"""
    migrations = [
        {
            "sql": """
            ALTER TABLE users ADD COLUMN last_activity TIMESTAMP;
            """,
            "description": "Add last_activity column to users table"
        },
        {
            "sql": """
            CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
            """,
            "description": "Add index on last_activity column"
        }
    ]
    
    for migration in migrations:
        run_migration(migration["sql"], migration["description"])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <version>")
        print("Available versions: v2")
        sys.exit(1)
    
    version = sys.argv[1]
    
    if version == "v2":
        migrate_to_v2()
    else:
        print(f"Unknown migration version: {version}")
        sys.exit(1)
'''
        
        with open("migrate.py", "w") as f:
            f.write(migration_content)
        
        os.chmod("migrate.py", 0o755)
        logger.info("✅ Migration script created: migrate.py")
    
    def create_database_health_check(self):
        """Create database health check script"""
        health_check_content = '''#!/usr/bin/env python3
"""
Database Health Check Script
Verifies database connection and basic operations
"""
import os
import sys
import time
from backend.core.database import get_database_manager
from backend.models.models import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Check database connection"""
    try:
        db_manager = get_database_manager()
        
        # Test connection
        with db_manager.get_session() as session:
            result = session.execute("SELECT 1").fetchone()
            assert result[0] == 1
        
        logger.info("✅ Database connection: OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection: FAILED - {e}")
        return False

def check_tables():
    """Check if all required tables exist"""
    try:
        db_manager = get_database_manager()
        
        # Check if we can query the users table
        with db_manager.get_session() as session:
            session.query(User).count()
        
        logger.info("✅ Database tables: OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database tables: FAILED - {e}")
        return False

def check_performance():
    """Check database performance"""
    try:
        start_time = time.time()
        
        db_manager = get_database_manager()
        with db_manager.get_session() as session:
            # Simple performance test
            for _ in range(10):
                session.execute("SELECT 1")
        
        elapsed_time = time.time() - start_time
        
        if elapsed_time < 1.0:
            logger.info(f"✅ Database performance: OK ({elapsed_time:.2f}s)")
            return True
        else:
            logger.warning(f"⚠️  Database performance: SLOW ({elapsed_time:.2f}s)")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database performance: FAILED - {e}")
        return False

def main():
    """Run all health checks"""
    logger.info("🔍 Running database health checks...")
    
    checks = [
        ("Connection", check_database_connection),
        ("Tables", check_tables),
        ("Performance", check_performance)
    ]
    
    results = []
    for name, check_func in checks:
        logger.info(f"Checking {name}...")
        result = check_func()
        results.append((name, result))
    
    logger.info("📊 Health Check Results:")
    all_passed = True
    for name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"   {name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        logger.info("✅ All database health checks passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some database health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open("database_health_check.py", "w") as f:
            f.write(health_check_content)
        
        os.chmod("database_health_check.py", 0o755)
        logger.info("✅ Database health check script created: database_health_check.py")
    
    def create_all_production_files(self):
        """Create all production database files"""
        logger.info("🚀 Creating production database setup...")
        
        # Create backup first
        try:
            backup_path = self.create_backup()
            if backup_path:
                logger.info(f"Current database backed up to: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
        
        # Create all files
        self.create_production_env()
        self.create_database_init_script()
        self.create_docker_compose()
        self.create_migration_script()
        self.create_database_health_check()
        
        logger.info("✅ Production database setup completed!")
        logger.info("")
        logger.info("📋 Created files:")
        logger.info("   - .env.production (production environment variables)")
        logger.info("   - init_production_db.sh (database initialization)")
        logger.info("   - docker-compose.prod.yml (production services)")
        logger.info("   - migrate.py (database migrations)")
        logger.info("   - database_health_check.py (health monitoring)")
        logger.info("")
        logger.info("🚀 Next steps:")
        logger.info("   1. Review and update .env.production with your settings")
        logger.info("   2. Run ./init_production_db.sh to initialize database")
        logger.info("   3. Test with ./database_health_check.py")
        logger.info("   4. Optional: Use docker-compose -f docker-compose.prod.yml up for services")

def main():
    """Command line interface"""
    import sys
    
    prod_db = ProductionDatabase()
    
    if len(sys.argv) < 2:
        print("Usage: python production_database.py <command>")
        print("Commands:")
        print("  create-all    Create all production database files")
        print("  create-env    Create production environment file")
        print("  create-init   Create database initialization script")
        print("  create-docker Create Docker Compose file")
        print("  backup        Create database backup")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create-all":
        prod_db.create_all_production_files()
    elif command == "create-env":
        prod_db.create_production_env()
    elif command == "create-init":
        prod_db.create_database_init_script()
    elif command == "create-docker":
        prod_db.create_docker_compose()
    elif command == "backup":
        backup_path = prod_db.create_backup()
        print(f"Backup created: {backup_path}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
