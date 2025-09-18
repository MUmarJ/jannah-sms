# Jannah SMS Admin v2.0

A modern, elderly-friendly SMS management system for property management with automated scheduling and conditional messaging.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)

## 🌟 Features

### Core Functionality
- **📱 SMS Management** - Send individual or bulk SMS messages via TextBelt API
- **⏰ Automated Scheduling** - Create recurring schedules with advanced conditional logic
- **👥 Tenant Management** - Comprehensive tenant database with payment tracking
- **📊 Dashboard** - Real-time overview with statistics and recent activity
- **💰 Payment Tracking** - Track rent payments, late fees, and payment history
- **📋 Message Templates** - Pre-built templates for common messages

### Conditional Logic Engine
- Send messages based on payment status (`isPaid`, `isOverdue`)
- Target specific tenant groups with complex conditions
- Schedule messages for specific dates and times
- Automatic late fee notifications and rent reminders

### Elderly-Friendly Design
- **Large fonts** (18px+ base size) for easy reading
- **High contrast** colors for better visibility
- **Simple navigation** with clear, descriptive buttons
- **Minimal complexity** with intuitive workflows
- **Accessible** design with keyboard navigation and screen reader support

### Security & Production Ready
- JWT-based authentication with session cookies
- SQL injection protection with SQLAlchemy ORM
- Input validation and sanitization
- Rate limiting and CORS protection
- Docker containerization for easy deployment

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional but recommended)
- TextBelt API key (get from [textbelt.com](https://textbelt.com))

### Option 1: Docker Deployment (Recommended)

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd jannah-sms-fastapi
   cp .env.example .env
   ```

2. **Configure environment**:
   Edit `.env` file with your settings:
   ```bash
   SMS_API_KEY=your-textbelt-api-key-here
   SECRET_KEY=your-very-secret-key-change-this-in-production
   ADMIN_PASSWORD=your-secure-admin-password
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs
   - Login with username: `admin`, password: (as set in .env)

### Option 2: Local Development

1. **Setup Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 📖 Usage Guide

### Dashboard
The main dashboard provides:
- Tenant statistics (total, paid, unpaid, late fees)
- Active schedules count
- Messages sent today and success rate
- Recent message activity
- Upcoming scheduled messages

### Managing Tenants
1. **Add Tenants**: Click "Add Tenant" to create new tenant records
2. **Import from CSV**: Use "Import" button to bulk upload from spreadsheet
3. **Payment Status**: Mark tenants as paid/unpaid for current month
4. **Search & Filter**: Find tenants by name, phone, unit, or payment status

### Sending Messages
1. **Individual Messages**: Select recipients and compose message
2. **Template Messages**: Use pre-built templates for common scenarios
3. **Bulk Messaging**: Send to all tenants, paid tenants, unpaid tenants, or custom selection
4. **Scheduling**: Send immediately or schedule for specific date/time

### Automated Schedules
1. **Create Schedule**: Set up recurring messages with conditional logic
2. **Conditions**: Target specific tenant groups (unpaid rent, late fees, etc.)
3. **Templates**: Use built-in templates or create custom messages
4. **Monitoring**: View execution history and success rates

## 🏗️ Architecture

```
jannah-sms-fastapi/
├── app/
│   ├── api/v1/          # REST API endpoints
│   ├── core/            # Configuration and database
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic services
│   ├── static/          # CSS, JS, images
│   ├── templates/       # HTML templates
│   ├── web/             # Web interface routes
│   └── main.py          # FastAPI application
├── docker-compose.yml   # Container orchestration
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
└── README.md
```

### Key Components

- **FastAPI** - Modern web framework with automatic API documentation
- **SQLAlchemy** - Robust ORM for database operations  
- **APScheduler** - Advanced task scheduling with cron-like capabilities
- **Jinja2** - Template engine for server-side rendering
- **SQLite** - Lightweight database (easily upgradeable to PostgreSQL)
- **Docker** - Containerization for consistent deployments

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SMS_API_KEY` | TextBelt API key | Required |
| `SECRET_KEY` | JWT signing key | Generate secure key |
| `DATABASE_URL` | Database connection | `sqlite:///./jannah_sms.db` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin login password | `admin123` |
| `DEBUG` | Enable debug mode | `false` |

### Message Templates

Built-in templates include:
- **Rent Reminder**: Monthly rent payment reminders
- **Late Fee Notice**: Overdue payment notifications  
- **Payment Confirmation**: Payment received confirmations
- **Maintenance Notice**: Scheduled maintenance alerts
- **Custom**: Create your own templates

### Conditional Logic

Target tenants based on:
- Payment status (`is_current_month_rent_paid`)
- Late fee status (`late_fee_applicable`) 
- Last payment date
- Unit number ranges
- Custom combinations with AND/OR logic

## 🔒 Security

### Authentication
- JWT tokens for API access
- Session cookies for web interface
- Configurable token expiration
- Secure password hashing

### Input Validation
- Pydantic schemas for request validation
- SQL injection prevention via ORM
- XSS protection in templates
- File upload restrictions

### Production Considerations
- Change default admin credentials
- Use strong secret keys
- Enable HTTPS in production
- Regular database backups
- Monitor SMS quota usage

## 📊 API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Key Endpoints

- `GET /api/v1/tenants` - List tenants with filtering
- `POST /api/v1/messages/send` - Send SMS messages
- `GET /api/v1/schedules` - List automated schedules
- `POST /api/v1/schedules/{id}/run` - Execute schedule immediately

## 🐳 Docker Production Deployment

### Single Container
```bash
docker run -d \
  --name jannah-sms \
  -p 8000:8000 \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  -e SMS_API_KEY=your-key \
  -e SECRET_KEY=your-secret \
  jannah-sms:latest
```

### With Nginx Reverse Proxy
```bash
# Enable production profile with nginx
docker-compose --profile production up -d
```

### With Database Backups
```bash
# Enable backup service
docker-compose --profile production up -d
```

## 🔧 Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Linting
flake8 app/
pylint app/

# Type checking  
mypy app/

# Security scan
bandit -r app/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## 📚 Migration from v1.0

The new FastAPI version includes:

### New Features
- ✅ Advanced scheduling with conditional logic
- ✅ Comprehensive REST API
- ✅ Modern elderly-friendly UI
- ✅ Docker containerization
- ✅ Production-ready security

### Breaking Changes
- Database schema updated (auto-migrates)
- Configuration moved to environment variables
- Web interface redesigned for accessibility

### Migration Steps
1. Backup existing data: `cp app.db backup.db`
2. Export tenants to CSV from old system
3. Deploy new system with Docker
4. Import tenants via web interface
5. Set up new automated schedules

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**SMS not sending?**
- Check API key is correct
- Verify phone numbers are in correct format
- Check SMS quota remaining

**Can't login?**  
- Check admin credentials in .env file
- Clear browser cookies
- Restart application container

**Database errors?**
- Check file permissions on data directory
- Ensure sufficient disk space
- Review logs in `/app/logs/`

### Getting Help

- 📧 Email: support@jannah-sms.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/jannah-sms/issues)
- 📖 Documentation: [Full Documentation](https://docs.jannah-sms.com)

## 🎯 Roadmap

### v2.1 (Next Release)
- [ ] Multi-tenant support
- [ ] Email notifications
- [ ] Advanced reporting
- [ ] Mobile app integration

### v2.2 (Future)
- [ ] WhatsApp integration
- [ ] Voice call support
- [ ] Multi-language support
- [ ] Advanced analytics

---

**Built with ❤️ for property managers and their tenants**