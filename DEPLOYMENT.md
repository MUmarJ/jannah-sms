# Jannah SMS - Vercel Deployment Guide

## Overview
This guide covers deploying the Jannah SMS application to Vercel.

## Prerequisites
- Vercel account ([sign up here](https://vercel.com))
- Vercel CLI installed (optional): `npm install -g vercel`
- PostgreSQL database (recommended: [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) or [Supabase](https://supabase.com))

## Environment Variables

You need to set the following environment variables in your Vercel project:

### Required Variables

1. **DATABASE_URL** - PostgreSQL connection string
   ```
   postgresql://username:password@host:port/database
   ```

2. **SMS_API_KEY** - TextBelt API key for sending SMS
   ```
   textbelt_api_key_here
   ```

3. **SECRET_KEY** - Secret key for sessions/security
   ```
   your-secret-key-minimum-32-characters
   ```

### Optional Variables

4. **COMPANY_NAME** - Your company name (default: "Jannah Management")
   ```
   Your Company Name
   ```

5. **DEBUG** - Debug mode (default: false)
   ```
   false
   ```

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Push your code to GitHub/GitLab/Bitbucket**
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   git push origin main
   ```

2. **Import project in Vercel**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Select your repository
   - Vercel will auto-detect the configuration from `vercel.json`

3. **Configure Environment Variables**
   - Go to Project Settings → Environment Variables
   - Add all required environment variables listed above

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel
   ```

4. **Add environment variables**
   ```bash
   vercel env add DATABASE_URL
   vercel env add SMS_API_KEY
   vercel env add SECRET_KEY
   ```

5. **Redeploy with environment variables**
   ```bash
   vercel --prod
   ```

## Database Setup

### Using Vercel Postgres

1. **Create Postgres Database**
   - Go to your Vercel project
   - Navigate to Storage tab
   - Create a new Postgres database

2. **Copy Connection String**
   - Vercel will provide a `DATABASE_URL`
   - This is automatically added to your environment variables

3. **Run Migrations**
   The database tables will be automatically created on first run via `init_db()` in the application.

### Using External Database (Supabase, Railway, etc.)

1. Create a PostgreSQL database on your preferred provider
2. Get the connection string
3. Add it to Vercel environment variables as `DATABASE_URL`

## Post-Deployment

### 1. Test the Application
- Visit your Vercel URL (e.g., `https://your-app.vercel.app`)
- Check the homepage loads correctly
- Test tenant management features

### 2. Configure SMS API
- Update SMS API settings in the application
- Test sending messages in test mode first

### 3. Set up Opt-In Compliance
- Go to Tenants page
- Use the bulk opt-in selection to send opt-in requests
- Track tenant opt-in status

## Important Notes

### Limitations of Serverless
1. **Stateless Functions** - Each request runs in a separate serverless function
2. **Scheduler Service** - Background schedulers may not work in serverless mode
   - Consider using Vercel Cron Jobs for scheduled tasks
   - Or use external scheduler (e.g., GitHub Actions)

3. **Database Connections** - Use connection pooling for better performance
   - Recommended: Use Vercel Postgres with built-in pooling
   - Or configure SQLAlchemy connection pool settings

### Vercel Cron Jobs (for scheduled messages)

Create a file `vercel.json` cron section:
```json
{
  "crons": [
    {
      "path": "/api/v1/schedules/execute",
      "schedule": "0 9 * * *"
    }
  ]
}
```

## Troubleshooting

### Database Connection Issues
- Check DATABASE_URL format is correct
- Ensure database accepts external connections
- Verify SSL requirements (add `?sslmode=require` if needed)

### SMS Not Sending
- Verify SMS_API_KEY is correct
- Check TextBelt quota
- Test in test mode first

### Static Files Not Loading
- Ensure `app/templates/` and `app/static/` are not in `.vercelignore`
- Check file paths in templates are correct

### Cold Starts
- First request after inactivity may be slow
- Consider upgrading to Vercel Pro for better performance

## Monitoring

- **Logs**: View logs in Vercel Dashboard → Deployments → Select deployment → Logs
- **Analytics**: Enable Analytics in Project Settings
- **Errors**: Check Error tracking in Vercel Dashboard

## Support

For issues with:
- **Vercel Platform**: [Vercel Support](https://vercel.com/support)
- **Application**: Create an issue on GitHub repository
- **Database**: Refer to your database provider's documentation

## Next Steps

1. ✅ Set up custom domain in Vercel settings
2. ✅ Configure SMS webhook for replies
3. ✅ Enable Vercel Analytics
4. ✅ Set up monitoring and alerts
5. ✅ Regular backups of database
