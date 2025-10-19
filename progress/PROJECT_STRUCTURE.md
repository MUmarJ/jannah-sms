# Jannah SMS Admin - Project Structure

**Type:** FastAPI web application for property management SMS scheduling
**Status:** 85% complete - User Management & Railway Deployment Pending

---

## Tech Stack

- **Backend:** FastAPI 0.115, Python 3.11
- **Database:** SQLite (dev) / PostgreSQL (prod via Railway)
- **Auth:** JWT tokens + httpOnly cookies
- **SMS:** TextBelt API
- **Templates:** Jinja2
- **Deployment:** Railway.app (persistent processes)
- **Scheduler:** APScheduler (requires persistent processes)

### 🚨 Deployment Change
**Previous Plan:** Vercel (serverless)
**New Plan:** Railway.app
**Reason:** APScheduler requires persistent background processes, incompatible with Vercel serverless
**Impact:** Zero code changes needed, scheduler works as-is
**Cost:** ~$5-10/month

---

## Directory Structure

```
jannah-sms/
├── app/
│   ├── api/v1/              # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py          # ✅ Auth endpoints (login, register)
│   │   ├── messages.py      # SMS sending API
│   │   ├── schedules.py     # Schedule management API
│   │   └── tenants.py       # Tenant CRUD API
│   │
│   ├── core/                # Core configuration
│   │   ├── config.py        # ✅ Settings (Supabase added)
│   │   ├── database.py      # ✅ DB config (PostgreSQL support)
│   │   ├── security.py      # ✅ Auth helpers (JWT, bcrypt)
│   │   └── templates.py     # Jinja2 setup
│   │
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── message.py       # Message records
│   │   ├── schedule.py      # Scheduled messages
│   │   ├── tenant.py        # Tenant data (has opt-in fields)
│   │   └── user.py          # Admin users
│   │
│   ├── services/            # Business logic
│   │   ├── scheduler_service.py  # APScheduler wrapper
│   │   └── sms_service.py        # TextBelt SMS sending
│   │
│   ├── utils/               # Utilities
│   │   ├── __init__.py      # Utility module init
│   │   └── init_admin.py    # ✅ Admin creation utility
│   │
│   ├── web/                 # Web interface routes
│   │   ├── __init__.py
│   │   ├── auth.py          # ✅ Login/logout routes (rate limited)
│   │   ├── dashboard.py     # ✅ Main dashboard (protected)
│   │   ├── messages.py      # ✅ Message UI (protected, rate limited)
│   │   ├── schedules.py     # ✅ Schedule UI (protected)
│   │   └── tenants.py       # ✅ Tenant management UI (protected)
│   │
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html        # ✅ Base template (navbar, user display, logout)
│   │   ├── dashboard.html   # Main dashboard
│   │   ├── login.html       # ✅ Elderly-friendly login page
│   │   ├── messages.html    # Message sending UI
│   │   ├── schedules.html   # Schedule management
│   │   └── tenants.html     # Tenant list & CRUD
│   │
│   ├── static/              # CSS, JS, images
│   │   └── (empty - styles inline)
│   │
│   └── main.py              # FastAPI app entry point
│
├── api/
│   └── index.py             # Vercel serverless handler
│
├── progress/
│   ├── CONTINUATION_CONTEXT.md     # ✅ Updated with Railway decision
│   ├── RAILWAY_DEPLOYMENT_PLAN.md  # ✅ NEW - Full Railway deployment guide
│   ├── SESSION_SUMMARY_2025-10-12.md
│   ├── TEST_REPORT_2025-10-12.md
│   └── PROJECT_STRUCTURE.md        # This file
│
├── requirements.txt         # ✅ Dependencies (psycopg2, supabase added)
├── vercel.json              # Vercel deployment config
├── .env                     # Local environment (git-ignored)
├── .env.example             # Environment template
├── pyproject.toml           # Python project config
├── Dockerfile               # Docker deployment (optional)
├── docker-compose.yml       # Docker Compose (optional)
└── PROJECT_STRUCTURE.md     # This file
```

---

## Key Files & Their Purpose

### Core Application

| File | Purpose | Status | Lines |
|------|---------|--------|-------|
| `app/main.py` | FastAPI app, routes, middleware | ✅ Needs auth routes | ~200 |
| `app/core/config.py` | Environment variables, settings | ✅ Updated | ~120 |
| `app/core/database.py` | SQLAlchemy engine, PostgreSQL | ✅ Complete | ~75 |
| `app/core/security.py` | JWT, bcrypt, auth helpers | ✅ Fixed | ~160 |
| `app/core/templates.py` | Jinja2 configuration | ✅ Complete | ~20 |

### Authentication (Complete - Ready for Testing)

| File | Purpose | Status | Lines |
|------|---------|--------|-------|
| `app/api/v1/auth.py` | Auth API endpoints | ✅ Complete | 210 |
| `app/web/auth.py` | Login/logout routes | ✅ Complete | 91 |
| `app/templates/login.html` | Elderly-friendly login UI | ✅ Complete | ~150 |
| `app/utils/init_admin.py` | Admin user auto-creation | ✅ Complete | 60 |

### Models (SQLAlchemy + Pydantic)

| File | Purpose | Key Fields | Status |
|------|---------|------------|--------|
| `app/models/user.py` | Admin users | username, hashed_password, is_active, **pending_approval** | ⚠️ **JUST UPDATED** |
| `app/models/tenant.py` | Tenant data | name, contact, sms_opt_in_status | ✅ Complete |
| `app/models/message.py` | SMS records | tenant_id, content, status, sent_at | ✅ Complete |
| `app/models/schedule.py` | Recurring SMS | message_template, schedule_type, schedule_value | ✅ Complete |

**Recent Change:** User model now has `is_active=False` by default and `pending_approval=True` field for admin approval workflow.

### Web Interface Routes

| File | Routes | Protection Status |
|------|--------|-------------------|
| `app/web/dashboard.py` | `/dashboard` | ✅ Protected with `get_current_user` |
| `app/web/tenants.py` | `/tenants/*` (8 routes) | ✅ All protected |
| `app/web/messages.py` | `/messages/*` (3 routes) | ✅ All protected + rate limited |
| `app/web/schedules.py` | `/schedules/*` (5 routes) | ✅ All protected |
| `app/web/auth.py` | `/login`, `/logout` | ✅ Public (login only) + rate limited |

### API Routes

| File | Endpoints | Protection Status |
|------|-----------|-------------------|
| `app/api/v1/auth.py` | `/api/v1/auth/*` | ✅ Public (login/register only) |
| `app/api/v1/tenants.py` | `/api/v1/tenants/*` (15 routes) | ✅ All protected |
| `app/api/v1/messages.py` | `/api/v1/messages/*` (5 routes) | ✅ All protected |
| `app/api/v1/schedules.py` | `/api/v1/schedules/*` (10 routes) | ✅ All protected |

### Services

| File | Purpose | Key Functions |
|------|---------|---------------|
| `app/services/sms_service.py` | SMS sending via TextBelt | send_sms(), send_bulk_sms() |
| `app/services/scheduler_service.py` | Scheduled message execution | start(), stop(), execute_schedules() |

---

## Database Schema

### Users (for admin authentication)
```sql
users (
  id: Integer PK
  username: String(50) UNIQUE
  email: String(255) UNIQUE
  hashed_password: String(255)
  is_active: Boolean
  is_admin: Boolean
  last_login: DateTime
  login_count: Integer
  created_at: DateTime
)
```

### Tenants (property tenants)
```sql
tenants (
  id: Integer PK
  name: String(255)
  contact: String(20)
  rent: Integer
  building: String(255)
  sms_opt_in_status: String(20)  # pending, opted_in, opted_out
  sms_opt_in_date: DateTime
  initial_opt_in_message_sent: Boolean
  is_current_month_rent_paid: Boolean
  late_fee_applicable: Boolean
  created_at: DateTime
)
```

### Messages (SMS history)
```sql
messages (
  id: Integer PK
  tenant_id: Integer FK
  content: Text
  status: String  # sent, failed, pending
  sent_at: DateTime
  message_id: String  # TextBelt message ID
  test_mode: Boolean
)
```

### Schedules (recurring messages)
```sql
schedules (
  id: Integer PK
  name: String(255)
  message_template: Text
  schedule_type: String  # daily, weekly, monthly
  schedule_value: String  # "DD HH:MM" for monthly
  target_tenant_types: String
  status: String  # active, paused
  created_at: DateTime
)
```

---

## Configuration

### Environment Variables

**Required:**
```bash
DATABASE_URL=postgresql://...  # Supabase connection string
SECRET_KEY=...                 # 32+ char random string (JWT signing)
ADMIN_USERNAME=admin           # Initial admin username
ADMIN_PASSWORD=...             # Initial admin password
SMS_API_KEY=...                # TextBelt API key
```

**Optional:**
```bash
SUPABASE_URL=...               # For Supabase Auth integration
SUPABASE_ANON_KEY=...          # Supabase public key
DEBUG=false                    # Debug mode
SESSION_COOKIE_MAX_AGE=86400   # 24 hours
```

### Database Configuration

**Development (SQLite):**
```python
DATABASE_URL=sqlite:///./jannah_sms.db
```

**Production (PostgreSQL/Supabase):**
```python
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

**Connection Pooling (auto-configured):**
- SQLite: NullPool (no pooling)
- PostgreSQL: QueuePool (5 connections, 10 overflow)

---

## Authentication Flow

### Current Implementation
1. User visits site → redirects to `/login`
2. User enters credentials → POST `/login`
3. Backend verifies against `users` table
4. On success: JWT token created, httpOnly cookie set
5. Cookie sent with all requests
6. `get_current_user` dependency verifies token
7. Protected routes check authentication

### Token Details
- **Algorithm:** HS256
- **Expiry:** 60 minutes (or 30 days with "remember me")
- **Storage:** httpOnly cookie (XSS protection)
- **Secure:** True in production (HTTPS only)
- **SameSite:** lax (CSRF protection)

### Session Management
- Cookie name: `jannah_session` (configurable)
- Max age: 86400 seconds (24 hours default)
- Auto-renewal: No (must re-login after expiry)
- Logout: Deletes cookie

---

## Features Implemented

### ✅ Working Features (85% Complete - Code Ready)
1. Tenant management (CRUD)
2. SMS sending (individual & bulk)
3. Message templates
4. Scheduled recurring messages (monthly)
5. Opt-in tracking and compliance
6. Payment status tracking
7. Late fee management
8. Message history
9. Live message preview
10. Database (SQLite + PostgreSQL)
11. Auth API (JWT tokens)
12. Login page UI (elderly-friendly)
13. Route protection (all 47 routes)
14. User session management (httpOnly cookies)
15. Admin auto-initialization
16. Rate limiting (login: 5/min, messages: 10/min)
17. Security headers (XSS, clickjacking protection)

### ⏳ Testing Phase (15% Remaining)
18. Local testing (authentication flow, CRUD, SMS)
19. Production deployment (Vercel + Supabase)
20. End-to-end testing in production

### 📋 Future Enhancements
21. Audit logging
22. Password reset flow
23. 2FA (two-factor authentication)
24. Email notifications
25. Webhook integrations

---

## API Endpoints

### Authentication
```
POST   /api/v1/auth/login       # Login (get JWT)
POST   /api/v1/auth/logout      # Logout (clear cookie)
POST   /api/v1/auth/register    # Register user
GET    /api/v1/auth/me          # Get current user
GET    /api/v1/auth/check-setup # Check if admin exists
```

### Tenants
```
GET    /api/v1/tenants          # List tenants
POST   /api/v1/tenants          # Create tenant
GET    /api/v1/tenants/{id}     # Get tenant
PUT    /api/v1/tenants/{id}     # Update tenant
DELETE /api/v1/tenants/{id}     # Delete tenant (soft)
POST   /api/v1/tenants/{id}/mark-paid       # Mark paid
POST   /api/v1/tenants/{id}/send-opt-in     # Send opt-in
POST   /api/v1/tenants/send-bulk-opt-in     # Bulk opt-in
POST   /api/v1/tenants/bulk-mark-paid       # Bulk mark paid
GET    /api/v1/tenants/stats                # Statistics
```

### Messages
```
POST   /api/v1/messages/send                # Send SMS
GET    /api/v1/messages                     # Message history
POST   /api/v1/messages/send-rent-reminders # Bulk reminders
```

### Schedules
```
GET    /api/v1/schedules        # List schedules
POST   /api/v1/schedules        # Create schedule
GET    /api/v1/schedules/{id}   # Get schedule
PUT    /api/v1/schedules/{id}   # Update schedule
DELETE /api/v1/schedules/{id}   # Delete schedule
POST   /api/v1/schedules/execute # Execute now (admin)
```

---

## Deployment

### Local Development
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
python -m uvicorn app.main:app --reload
```

### Vercel Production
```bash
# 1. Create Supabase project
# 2. Set environment variables in Vercel dashboard
# 3. Deploy
vercel --prod
```

### Environment Setup
1. Create Supabase project at https://supabase.com
2. Get `DATABASE_URL` from Settings → Database
3. Generate `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
4. Set strong `ADMIN_PASSWORD`
5. Get `SMS_API_KEY` from https://textbelt.com

---

## Testing

### Manual Testing
```bash
# Test database connection
python -c "from app.core.database import engine; print(engine.url)"

# Test auth API
curl http://localhost:8000/api/v1/auth/check-setup

# Test registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

---

## Common Tasks

### Add New Protected Route
```python
from app.core.security import get_current_user

@router.get("/new-page")
async def new_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        "new_page.html",
        {
            "request": request,
            "current_user": current_user,
            # ... other context
        }
    )
```

### Create New Admin User
```python
from app.utils.init_admin import create_admin_user
from app.core.database import get_db_session

db = get_db_session()
create_admin_user(db, "newadmin", "password123", "admin@example.com")
```

### Debug Authentication
```python
# Check if user table exists
from app.core.database import get_db_session
from app.models.user import UserDB

db = get_db_session()
users = db.query(UserDB).all()
print(f"Users: {[u.username for u in users]}")
```

---

## Troubleshooting

### "No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### "Database connection failed"
- Check `DATABASE_URL` format
- Verify Supabase project is active
- Check firewall/network settings

### "Redirecting to /login in loop"
- Check `get_current_user` in security.py
- Verify JWT token is being created
- Check cookie settings (httpOnly, secure, samesite)

### "401 Unauthorized"
- Check if route has `Depends(get_current_user)`
- Verify token in cookie or Authorization header
- Check token hasn't expired

---

## Dependencies

### Core
- fastapi==0.115.13
- uvicorn[standard]==0.32.1
- sqlalchemy==2.0.36
- psycopg2-binary==2.9.9

### Auth
- python-jose[cryptography]==3.3.0
- passlib[bcrypt]==1.7.4

### Templates & Forms
- jinja2==3.1.4
- python-multipart==0.0.17

### Services
- aiohttp (SMS)
- apscheduler (scheduling)
- slowapi==0.1.9 (rate limiting)

### Optional
- supabase==2.10.0 (Supabase Auth)

---

## Project Status Summary

**Current State:** Authentication migration 85% complete (Code implementation finished)
**Next Milestone:** Testing & validation, then production deployment
**Time to MVP:** 30-60 minutes of testing
**Deployment Target:** Vercel with Supabase PostgreSQL

**What's Done:**
- ✅ All authentication code implemented
- ✅ All routes protected (47 total)
- ✅ Rate limiting active
- ✅ Security headers configured
- ✅ Admin auto-creation on startup
- ✅ Elderly-friendly login UI
- ✅ Deployment configuration complete

**What's Remaining:**
- ⏳ Local testing (verify login, CRUD, SMS)
- ⏳ Production deployment
- ⏳ Production smoke tests

**Continuation:** See `progress/CONTINUATION_CONTEXT.md` for detailed changes and testing steps

---

**Last Updated:** 2025-10-12 (Evening Session)
**Maintained By:** Development team
**Documentation:** README.md, DEPLOYMENT.md, progress/CONTINUATION_CONTEXT.md
