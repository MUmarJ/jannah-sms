#!/bin/bash

# Docker entrypoint script for Jannah SMS Admin
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Jannah SMS Admin...${NC}"

# Check if required environment variables are set
if [ -z "$SMS_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: SMS_API_KEY not set. SMS functionality will be disabled.${NC}"
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p /app/data
mkdir -p /app/logs

# Set permissions
echo -e "${BLUE}🔒 Setting permissions...${NC}"
chmod 755 /app/data
chmod 755 /app/logs

# Initialize database if it doesn't exist
if [ ! -f "/app/data/jannah_sms.db" ]; then
    echo -e "${GREEN}🗄️  Initializing database...${NC}"
    python -c "
from app.core.database import init_db
init_db()
print('Database initialized successfully!')
"
fi

# Check database health
echo -e "${BLUE}🔍 Checking database health...${NC}"
python -c "
try:
    from app.core.database import SessionLocal
    from app.models.tenant import Tenant
    
    with SessionLocal() as db:
        count = db.query(Tenant).count()
        print(f'Database OK - {count} tenants found')
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
"

# Test SMS API if key is provided
if [ -n "$SMS_API_KEY" ]; then
    echo -e "${BLUE}📱 Testing SMS API connection...${NC}"
    python -c "
import asyncio
from app.services.sms_service import sms_service

async def test_sms():
    try:
        result = await sms_service.test_api_key(test_mode=True)
        if result['success']:
            print('SMS API test successful')
            if 'quotaRemaining' in result:
                print(f'Quota remaining: {result[\"quotaRemaining\"]}')
        else:
            print(f'SMS API test failed: {result.get(\"error\", \"Unknown error\")}')
    except Exception as e:
        print(f'SMS API test error: {e}')

asyncio.run(test_sms())
"
fi

# Show configuration summary
echo -e "${GREEN}📋 Configuration Summary:${NC}"
echo -e "  ${BLUE}App Name:${NC} ${APP_NAME:-Jannah SMS Admin}"
echo -e "  ${BLUE}Company:${NC} ${COMPANY_NAME:-Jannah Property Management}"
echo -e "  ${BLUE}Debug Mode:${NC} ${DEBUG:-false}"
echo -e "  ${BLUE}Database:${NC} ${DATABASE_URL:-sqlite:///./data/jannah_sms.db}"
echo -e "  ${BLUE}SMS API:${NC} ${SMS_API_KEY:+Configured}${SMS_API_KEY:-Not configured}"

# Create admin user if it doesn't exist
echo -e "${BLUE}👤 Setting up admin user...${NC}"
python -c "
from app.core.database import SessionLocal
import os

admin_username = os.getenv('ADMIN_USERNAME', 'admin')
admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')

print(f'Admin username: {admin_username}')
if admin_password == 'admin123':
    print('⚠️  WARNING: Using default admin password. Please change in production!')
else:
    print('Admin password: [configured]')
"

echo -e "${GREEN}✅ Initialization complete!${NC}"
echo -e "${BLUE}🌐 Starting web server on port 8000...${NC}"

# Execute the main command
exec "$@"