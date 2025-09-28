# Financial Document Analyzer - Deployment Runbook

## Overview

This document provides step-by-step instructions for deploying the Financial Document Analyzer application in a production environment. The system consists of a FastAPI backend, React frontend, PostgreSQL database, and Redis cache.

## Prerequisites

### System Requirements
- Ubuntu 20.04 LTS or newer (recommended)
- Python 3.11.x
- Node.js 16.x or newer
- Docker and Docker Compose
- At least 4GB RAM, 2 CPU cores
- 20GB available disk space

### Required Accounts
- OpenAI API key (or compatible LLM service)
- Serper API key for search functionality
- NVIDIA NIM API key (optional, for alternative LLM)

## Deployment Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   Frontend      │    │    Backend       │    │   Services       │
│   (React)       │◄──►│   (FastAPI)      │◄──►│(PostgreSQL/Redis)│
└─────────────────┘    └──────────────────┘    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Observability  │
                    │   (OpenTelemetry)│
                    └──────────────────┘
```

## Step-by-Step Deployment

### 1. Environment Setup

#### Install System Dependencies
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and development tools
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install -y nodejs

# Install Docker
sudo apt install -y docker.io docker-compose

# Add current user to docker group
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

#### Clone Repository
```bash
git clone <repository-url>
cd wingily-project
```

### 2. Backend Deployment

#### Create Python Virtual Environment
```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Install Python Dependencies
```bash
# Install production dependencies
pip install -r requirements_updated.txt
```

#### Configure Environment Variables
```bash
# Copy production environment template
cp .env.production .env

# Edit environment variables
nano .env
```

Key variables to configure:
- `SECRET_KEY`: Generate a secure random key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `OPENAI_API_KEY`: Your OpenAI API key
- `SERPER_API_KEY`: Your Serper API key

#### Initialize Database
```bash
# Run database initialization script
./init_production_db.sh

# Run authentication schema migration
python migrate_auth_schema.py
```

#### Start Backend Services
```bash
# Start database and cache services
docker-compose -f docker-compose.prod.yml up -d

# Verify services are running
docker-compose -f docker-compose.prod.yml ps

# Start the FastAPI application
gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app
```

### 3. Frontend Deployment

#### Install Frontend Dependencies
```bash
cd frontend

# Install npm packages
npm install
```

#### Build Production Frontend
```bash
# Create production build
npm run build
```

#### Serve Frontend
```bash
# Option 1: Using a web server like Nginx (recommended for production)
# Install Nginx
sudo apt install nginx

# Configure Nginx (see Nginx Configuration section below)

# Option 2: Using serve package for quick deployment
npx serve -s build
```

### 4. Production Configuration

#### Environment Variables (.env)
```bash
# Database Configuration
DATABASE_URL=postgresql://financial_user:secure_password@localhost:5432/financial_analyzer_prod
DATABASE_DEBUG=false

# Database Connection Pool Settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# File Storage Configuration
KEEP_UPLOADED_FILES=true
MAX_STORED_FILES_PER_USER=50
FILE_CLEANUP_DAYS=30

# Security Settings
SECRET_KEY=your-very-secure-secret-key-here
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
```

#### Nginx Configuration
Create `/etc/nginx/sites-available/financial-analyzer`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend static files
    location / {
        root /path/to/frontend/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/financial-analyzer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Production Monitoring

#### Health Checks
```bash
# Application health check
curl http://localhost:8000/health

# Database health check
./database_health_check.py

# Redis cache stats
curl http://localhost:8000/cache/stats
```

#### Log Monitoring
```bash
# Application logs
tail -f logs/financial_analyzer.log

# Docker service logs
docker-compose -f docker-compose.prod.yml logs -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 6. Backup and Maintenance

#### Database Backup
```bash
# Create database backup
python production_database.py backup

# Automated backup script (add to crontab)
0 2 * * * cd /path/to/project && python production_database.py backup
```

#### Routine Maintenance
```bash
# Clean up old files
python -c "from file_manager import get_file_manager; fm = get_file_manager(); fm.perform_maintenance()"

# Check storage statistics
curl http://localhost:8000/admin/storage-stats
```

## Scaling Considerations

### Horizontal Scaling
1. **Load Balancer**: Deploy multiple backend instances behind a load balancer
2. **Database Replication**: Set up PostgreSQL read replicas for read-heavy operations
3. **Redis Clustering**: Implement Redis cluster for distributed caching
4. **Message Queue**: Use Celery with Redis/RabbitMQ for distributed task processing

### Vertical Scaling
1. **Increase Resources**: Add more CPU/RAM to existing instances
2. **Database Optimization**: Tune PostgreSQL settings for better performance
3. **Caching Strategy**: Expand Redis memory and optimize cache keys

## Troubleshooting

### Common Issues and Solutions

#### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.prod.yml ps

# Check database connectivity
python -c "from database import get_database_manager; print(get_database_manager().health_check())"
```

#### Redis Connection Issues
```bash
# Check if Redis is running
docker-compose -f docker-compose.prod.yml ps redis

# Test Redis connectivity
redis-cli ping
```

#### Application Startup Issues
```bash
# Check application logs
tail -f logs/financial_analyzer.log

# Run health check
curl http://localhost:8000/health
```

#### Performance Issues
```bash
# Monitor system resources
htop

# Check database performance
python database_health_check.py

# Check cache statistics
curl http://localhost:8000/cache/stats
```

## Security Best Practices

### Network Security
- Use HTTPS with valid SSL certificates
- Implement firewall rules to restrict access
- Regular security updates for all components
- Monitor for suspicious activity

### Application Security
- Regular dependency updates and security scans
- Input validation and sanitization
- Secure API rate limiting
- Regular security audits

### Data Security
- Database encryption at rest
- Regular backups with encryption
- Secure file storage and access controls
- Data retention and deletion policies

## Rollback Procedure

### In Case of Deployment Failure
1. **Stop new services**:
   ```bash
   pkill gunicorn
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore database from backup**:
   ```bash
   # Copy backup file to database container
   docker cp backup_file postgres_container:/backups/
   
   # Restore database (specific commands depend on database type)
   ```

3. **Revert to previous version**:
   ```bash
   git checkout <previous-stable-commit>
   ```

4. **Restart services**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app
   ```

## Maintenance Schedule

### Daily
- Check application and service health
- Monitor logs for errors
- Verify backup completion

### Weekly
- Update system packages
- Review security logs
- Performance monitoring

### Monthly
- Security audits
- Dependency updates
- Database maintenance and optimization

## Contact Information

For deployment issues, contact:
- System Administrator: [admin@yourcompany.com]
- Development Team: [dev@yourcompany.com]

---

*This document should be reviewed and updated regularly to reflect changes in the deployment process and system architecture.*