# Jannah SMS - Railway Deployment Guide

## Overview
This guide covers deploying the Jannah SMS application to Railway.app - the recommended platform for this application due to APScheduler's requirement for persistent processes.

## Why Railway?
- ✅ **Persistent Processes**: APScheduler requires a long-running process (not compatible with serverless)
- ✅ **Simple Setup**: One-click PostgreSQL provisioning
- ✅ **Auto-scaling**: Handles traffic spikes automatically
- ✅ **Cost Effective**: ~$5-10/month for app + database
- ✅ **Zero Configuration**: No need for separate API handlers

## Prerequisites
- Railway account ([sign up here](https://railway.app))
- GitHub account (for deployment)
- TextBelt API key ([get one here](https://textbelt.com))

## Quick Start (5 minutes)

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2. Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository
5. Railway will automatically detect the Python app

### 3. Add PostgreSQL Database

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically:
   - Provision a PostgreSQL instance
   - Set the `DATABASE_URL` environment variable
   - Connect it to your application

### 4. Configure Environment Variables

In Railway dashboard → **Variables** tab, add:

#### Required Variables

```bash
# Security (CRITICAL - Generate a strong key!)
SECRET_KEY=your-secret-key-here-minimum-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Admin User (Change password!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here
ADMIN_EMAIL=admin@yourdomain.com

# SMS API
SMS_API_KEY=your-textbelt-api-key
SMS_API_BASE=https://textbelt.com/text

# Session Configuration
SESSION_COOKIE_NAME=jannah_session
SESSION_COOKIE_MAX_AGE=86400
```

#### Optional Variables

```bash
# Application Branding
APP_NAME=Jannah SMS Admin
COMPANY_NAME=Your Company Name
APP_VERSION=v2.0
PRIMARY_COLOR=#3b82f6

# Production Settings
DEBUG=false
LOG_LEVEL=INFO
```

**Note:** `DATABASE_URL` is automatically provided by Railway when you add PostgreSQL.

### 5. Generate SECRET_KEY

Run locally to generate a secure key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and paste it as your `SECRET_KEY` in Railway.

### 6. Deploy!

Railway will automatically:
1. Install dependencies from `requirements.txt`
2. Run database migrations
3. Create admin user on first startup
4. Start the scheduler service
5. Deploy your application

Your app will be available at: `https://your-app-name.railway.app`

## Post-Deployment

### First Login

1. Visit your Railway URL
2. Login with your `ADMIN_USERNAME` and `ADMIN_PASSWORD`
3. You should see the dashboard with 0 tenants

### Add Tenants

1. Click **"Tenants"** in navigation
2. Click **"Add Tenant"**
3. Fill in tenant information
4. Click **"Save"**

### Test SMS

1. Go to **"Messages"** → **"Send Message"**
2. Select a tenant
3. Compose and send a test message
4. Verify it arrives at the phone number

## Monitoring & Logs

### View Application Logs

In Railway dashboard:
1. Click on your service
2. Go to **"Deployments"** tab
3. Click on the latest deployment
4. View real-time logs

Look for:
- ✅ Database initialized
- ✅ Admin user created
- ✅ Scheduler service started
- ✅ Application startup complete

### Common Log Messages

**Success:**
```
✅ Database initialized at: postgresql://...
✅ Admin user created from environment variables
⏰ Scheduler service started successfully
✅ Application startup complete
```

**Issues:**
```
⚠️  NO USERS FOUND!
🔧 Set ADMIN_PASSWORD in environment to auto-create admin
```

## Database Management

### View Database

Railway provides a built-in PostgreSQL client:
1. Click on your PostgreSQL service
2. Go to **"Data"** tab
3. Browse tables and data

### Backup Database

Railway automatically backs up your database. To manually export:

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Link project:
   ```bash
   railway link
   ```

4. Connect to database:
   ```bash
   railway connect postgres
   ```

5. Export data:
   ```bash
   pg_dump $DATABASE_URL > backup.sql
   ```

## Custom Domain (Optional)

1. In Railway dashboard → **Settings** → **Domains**
2. Click **"Add Domain"**
3. Enter your custom domain (e.g., `sms.yourdomain.com`)
4. Add CNAME record to your DNS:
   - Name: `sms` (or your subdomain)
   - Value: Provided by Railway
   - TTL: 300

## Scaling

Railway auto-scales based on traffic. To configure:

1. Go to **Settings** → **Resources**
2. Adjust:
   - **Memory**: 512MB minimum (recommended: 1GB)
   - **vCPU**: 1 vCPU minimum
   - **Replicas**: 1 for starter, 2+ for production

## Estimated Costs

### Development/Testing
- **App Instance**: $5/month (512MB RAM, 0.5 vCPU)
- **PostgreSQL**: $5/month (Small instance)
- **Total**: ~$10/month

### Production (Small)
- **App Instance**: $10/month (1GB RAM, 1 vCPU)
- **PostgreSQL**: $10/month (Medium instance)
- **Total**: ~$20/month

Railway provides $5 free credits/month for hobby plan.

## Troubleshooting

### App won't start

**Check logs for errors:**
```bash
railway logs
```

**Common issues:**
- Missing environment variables → Add in Railway dashboard
- Database not connected → Ensure PostgreSQL service is added
- Wrong Python version → Railway auto-detects from `runtime.txt`

### Database connection failed

**Check DATABASE_URL:**
```bash
railway variables
```

Ensure it starts with `postgresql://` and is provided by Railway's PostgreSQL service.

### Admin user not created

**Check logs:**
```
⚠️  NO USERS FOUND!
```

**Solution:** Ensure `ADMIN_PASSWORD` is set in environment variables (not "changeme").

### Scheduler not running

**Check logs for:**
```
⏰ Scheduler service started successfully
```

**If missing:**
- APScheduler failed to start
- Check for errors in logs
- Verify `requirements.txt` includes `apscheduler`

## Security Checklist

Before going to production:

- [ ] Changed `ADMIN_PASSWORD` from default
- [ ] Generated strong `SECRET_KEY` (32+ characters)
- [ ] Set `DEBUG=false`
- [ ] Using HTTPS (automatic on Railway)
- [ ] Custom domain configured (optional)
- [ ] Database backups enabled (automatic)
- [ ] Reviewed environment variables
- [ ] Tested SMS functionality
- [ ] Tested schedule creation

## Support

**Issues?** Check:
- Railway Status: [status.railway.app](https://status.railway.app)
- Railway Docs: [docs.railway.app](https://docs.railway.app)
- Project Issues: [GitHub Issues](https://github.com/yourusername/jannah-sms/issues)

## Next Steps

1. ✅ Deploy to Railway
2. ✅ Configure environment variables
3. ✅ Test admin login
4. ✅ Add tenants
5. ✅ Send test messages
6. ✅ Create scheduled messages
7. 🎉 Monitor and maintain!

---

**Last Updated**: 2025-10-13
**Platform**: Railway.app
**Compatibility**: Jannah SMS v2.0+
