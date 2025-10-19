# Webhook Configuration Guide

## Overview
This guide explains how to configure webhooks to receive SMS replies from tenants, enabling two-way SMS communication and automatic opt-in/opt-out processing.

## What is the Webhook?

The webhook is an endpoint on your server that TextBelt calls when a tenant replies to your SMS messages. This enables:

- ✅ **Automatic Opt-in Processing**: When tenants reply "YES" to opt-in requests
- ✅ **Automatic Opt-out Processing**: When tenants reply "STOP" to unsubscribe
- ✅ **A2P Compliance**: Required for Application-to-Person messaging regulations
- ✅ **Message History**: All replies are saved for review
- ✅ **Tenant Communication**: Track tenant responses

## How It Works

```
1. Your App sends SMS to tenant via TextBelt
   ↓
2. Tenant receives message and replies
   ↓
3. TextBelt receives reply
   ↓
4. TextBelt calls YOUR webhook with reply data
   ↓
5. Your app processes the reply:
   - If "YES"/"START" → Mark tenant as opted-in
   - If "STOP" → Mark tenant as opted-out
   - Otherwise → Save for manual review
   ↓
6. Your app sends confirmation message
```

## Webhook Endpoint

**URL:** `https://your-domain.com/api/v1/webhooks/sms-reply`

**Method:** `POST`

**Code Location:** [app/api/v1/webhooks.py](app/api/v1/webhooks.py:35)

## Configuration Steps

### Step 1: Deploy Your Application

Before configuring webhooks, your application must be accessible from the internet:

#### Railway Deployment
```bash
# Follow DEPLOYMENT.md to deploy to Railway
# Your app will be available at: https://your-app-name.railway.app
```

#### Custom Domain (Optional)
```bash
# Configure custom domain in Railway dashboard
# Your app will be at: https://sms.yourdomain.com
```

### Step 2: Set Webhook URL

After deployment, update your environment variable:

#### In Railway Dashboard
1. Go to your project → **Variables**
2. Click **+ New Variable**
3. Add:
   ```
   Name: WEBHOOK_URL
   Value: https://your-app-name.railway.app/api/v1/webhooks/sms-reply
   ```

#### In Local .env (for testing)
```bash
# .env
WEBHOOK_URL=https://your-ngrok-url.ngrok.io/api/v1/webhooks/sms-reply
```

**Note:** For local testing, use [ngrok](https://ngrok.com) to expose your local server:
```bash
ngrok http 8000
# Use the HTTPS URL provided by ngrok
```

### Step 3: Verify Configuration

Check that webhook URL is configured:

```bash
# Method 1: Check environment
curl https://your-app-name.railway.app/health

# Method 2: Check logs
# In Railway, view deployment logs to see:
# "Webhook URL configured: https://..."
```

### Step 4: Test Webhook

#### Test Locally
```bash
# Send a test webhook request
curl -X POST http://localhost:8000/api/v1/webhooks/sms-reply \
  -H "Content-Type: application/json" \
  -d '{
    "textId": "test-123",
    "fromNumber": "+15555551234",
    "text": "YES"
  }'

# Expected response:
# {"status": "success", "reply_id": 1}
```

#### Test in Production
1. Send an SMS to a tenant
2. Have them reply with "YES"
3. Check application logs for:
   ```
   Received SMS reply: {...}
   Processing opt-in for tenant X
   Sent opt-in confirmation
   ```

## Webhook Payload

TextBelt sends this data to your webhook:

```json
{
  "textId": "123456789",         // Original message ID
  "fromNumber": "+15555551234",  // Tenant's phone number
  "text": "YES",                 // Reply text
  "timestamp": 1697234567        // Unix timestamp
}
```

Your webhook processes this and returns:

```json
{
  "status": "success",
  "reply_id": 42
}
```

## Automatic Processing

### Opt-in Keywords (Case Insensitive)
- `YES`
- `Y`
- `START`
- `UNSTOP`
- `JOIN`
- `SUBSCRIBE`

**What Happens:**
1. Tenant status → `opted_in`
2. `sms_opt_in_date` → current timestamp
3. Confirmation message sent:
   ```
   "Thank you! You're now subscribed to Jannah Property Management
   SMS notifications. Reply STOP at any time to unsubscribe."
   ```

### Opt-out Keywords (Case Insensitive)
- `STOP`
- `STOPALL`
- `UNSUBSCRIBE`
- `CANCEL`
- `END`
- `QUIT`

**What Happens:**
1. Tenant status → `opted_out`
2. `sms_opt_out_date` → current timestamp
3. Confirmation message sent:
   ```
   "You've been unsubscribed from Jannah Property Management SMS
   notifications. Reply YES at any time to resubscribe."
   ```

### Other Replies
Any other text is saved to the database for manual review in the Messages section.

## Viewing Replies

### In the Application
1. Go to **Messages** → **Replies**
2. View all tenant replies with:
   - Original message sent
   - Reply text
   - Timestamp
   - Processing status
   - Tenant name

### In Database
```sql
SELECT * FROM message_replies
ORDER BY received_at DESC
LIMIT 10;
```

## Security

### Webhook Security Measures
1. **HTTPS Only**: Webhook URL must use HTTPS in production
2. **Validation**: Phone numbers are validated and normalized
3. **Error Handling**: Failed webhooks don't crash the system
4. **Logging**: All webhook requests are logged for audit

### Optional: Add Webhook Secret
For enhanced security, you can add webhook signature verification:

```python
# In app/api/v1/webhooks.py
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Troubleshooting

### Webhook Not Receiving Requests

**Check 1: Is webhook URL set?**
```bash
# In Railway variables, verify WEBHOOK_URL is set
echo $WEBHOOK_URL
```

**Check 2: Is endpoint accessible?**
```bash
curl https://your-app-name.railway.app/api/v1/webhooks/sms-reply
# Should return 422 (method not allowed) not 404
```

**Check 3: Check TextBelt configuration**
```bash
# TextBelt must be configured to call your webhook
# Check TextBelt dashboard/API settings
```

### Replies Not Being Processed

**Check Logs:**
```
2025-10-13 13:00:00 INFO: Received SMS reply: {"textId": "123", ...}
2025-10-13 13:00:01 INFO: Processing opt-in for tenant 5 (John Doe)
2025-10-13 13:00:02 INFO: Sent opt-in confirmation to John Doe
```

**If missing:**
- Verify webhook URL is correctly set
- Check that application is running
- Verify tenant phone number matches

### Tenant Not Found

```
WARNING: Tenant not found for phone number: +15555551234
```

**Solution:**
- Ensure tenant's phone number in database matches reply number
- Phone numbers are matched by last 10 digits
- Check for formatting differences (spaces, dashes, etc.)

## Testing Checklist

Before going live:

- [ ] Webhook URL configured in environment
- [ ] Application deployed and accessible
- [ ] HTTPS enabled (automatic on Railway)
- [ ] Test opt-in reply ("YES")
- [ ] Test opt-out reply ("STOP")
- [ ] Verify confirmation messages sent
- [ ] Check database for saved replies
- [ ] Review application logs for errors
- [ ] Test with unknown phone number

## Advanced Configuration

### Custom Reply Processing

To add custom automated responses:

```python
# In app/api/v1/webhooks.py

def _is_payment_confirmation(text: str) -> bool:
    """Check if reply is payment confirmation."""
    normalized = text.strip().upper()
    return "PAID" in normalized or "PAYMENT" in normalized

# In receive_sms_reply function:
elif _is_payment_confirmation(payload.text):
    # Mark tenant rent as paid
    tenant.is_current_month_rent_paid = True
    reply.processed = True
    # Send confirmation
```

### Webhook Retry Logic

If your webhook fails, TextBelt may retry. Handle idempotency:

```python
# Check if reply already processed
existing = db.query(MessageReply).filter(
    MessageReply.text_id == payload.textId
).first()

if existing:
    return {"status": "already_processed", "reply_id": existing.id}
```

## Cost Implications

**TextBelt Webhook Calls:**
- Free to receive
- No additional charges
- Only pay for outgoing SMS

**Railway Bandwidth:**
- Minimal impact
- Webhook payloads are small (~1KB each)

## Summary

### Configuration Required:
1. ✅ Deploy application to Railway
2. ✅ Set `WEBHOOK_URL` environment variable
3. ✅ Verify endpoint is accessible via HTTPS

### What You Get:
- ✅ Automatic opt-in/opt-out processing
- ✅ A2P compliance
- ✅ Reply history and tracking
- ✅ Tenant communication monitoring

### Maintenance:
- 🔄 Monitor webhook logs regularly
- 🔄 Review unprocessed replies
- 🔄 Update opt-in/opt-out keywords as needed

---

**Need Help?** Check:
- Application logs in Railway dashboard
- Database `message_replies` table
- [app/api/v1/webhooks.py](app/api/v1/webhooks.py) source code

**Last Updated:** 2025-10-13
**Status:** ✅ Ready for configuration
