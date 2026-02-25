# Weekly Analytics Report Setup Guide

This guide explains how to set up and use the automated weekly analytics reporting system for Neunet.

## Features

The analytics system tracks:
- **User Activity**: Login/logout timestamps, IP addresses, user agents
- **Session Statistics**: Total time spent, average session duration, number of logins
- **User Feedback**: All feedback submissions with categories and timestamps
- **Summary Metrics**: Active users, total logins, total feedback, total hours spent

## Setup Instructions

### 1. Configure Email Settings (Required for Automated Emails)

Add these environment variables to your Render deployment:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

**For Gmail:**
1. Go to Google Account Settings → Security
2. Enable 2-Factor Authentication
3. Generate an App Password (https://myaccount.google.com/apppasswords)
4. Use the generated password as `SENDER_PASSWORD`

**For Other Email Providers:**
- **Outlook/Hotmail**: `smtp.office365.com:587`
- **Yahoo**: `smtp.mail.yahoo.com:587`
- **SendGrid**: `smtp.sendgrid.net:587`

### 2. Set Up GitHub Secrets

For automated weekly emails via GitHub Actions:

1. Go to your GitHub repository: https://github.com/Idea-by-Design/Neunet-Backend-deployment
2. Navigate to Settings → Secrets and variables → Actions
3. Add a new secret:
   - Name: `REPORT_EMAIL`
   - Value: Your email address (e.g., `astha@neunet.io`)

### 3. Deploy the Backend

```bash
cd /Users/astha/Neunet-Backend-deployment
git add .
git commit -m "Add weekly analytics report system with email automation"
git push origin main
```

Wait for Render to deploy the changes (check deployment logs at https://dashboard.render.com).

## Usage

### Option 1: Manual API Access

Get the analytics report anytime via API:

```bash
# Weekly report (last 7 days)
curl https://neunet-ai-services.onrender.com/api/auth/analytics/weekly-report?days=7

# Monthly report (last 30 days)
curl https://neunet-ai-services.onrender.com/api/auth/analytics/weekly-report?days=30

# Custom period (e.g., last 14 days)
curl https://neunet-ai-services.onrender.com/api/auth/analytics/weekly-report?days=14
```

### Option 2: Send Email On-Demand

Trigger an email report manually:

```bash
curl -X POST "https://neunet-ai-services.onrender.com/api/auth/analytics/send-weekly-report?recipient_email=your-email@example.com&days=7"
```

### Option 3: Automated Weekly Emails

Once set up, the system will automatically:
- **Run every Monday at 9:00 AM UTC (2:30 PM IST)**
- Generate a report for the past 7 days
- Send a beautifully formatted HTML email to your configured email address

**Manual Trigger:**
You can also manually trigger the weekly report from GitHub:
1. Go to Actions tab in your repository
2. Select "Weekly Analytics Report"
3. Click "Run workflow"

## Report Contents

The email report includes:

### Summary Dashboard
- Active Users (users with activity in the period)
- Total Logins
- Total Feedback Submissions
- Total Hours Spent on Platform

### User Activity Table
Quick overview of all active users with:
- Name and email
- Number of logins
- Hours spent
- Feedback count

### Detailed User Sections
For each active user:
- Company size
- Last login timestamp
- All feedback submissions with timestamps
- Activity summary (logins, hours, average session duration)

## Troubleshooting

### Email Not Sending
1. Check environment variables are set correctly in Render
2. Verify SMTP credentials are valid
3. Check Render logs for error messages
4. For Gmail, ensure App Password is used (not regular password)

### GitHub Action Not Running
1. Verify `REPORT_EMAIL` secret is set in GitHub
2. Check Actions tab for workflow run history
3. Ensure the workflow file is in `.github/workflows/` directory

### No Data in Report
1. Verify users are logging in/out (check Cosmos DB)
2. Ensure logout tracking is working (test manually)
3. Check that activity logging is enabled in the backend

## Data Storage

All data is stored in Cosmos DB `users` container:

```json
{
  "email": "user@example.com",
  "name": "User Name",
  "activity_logs": [
    {
      "activity_id": "uuid",
      "type": "login",
      "timestamp": "2026-02-25T10:30:00.000000",
      "metadata": {
        "ip": "192.168.1.1",
        "user_agent": "Mozilla/5.0..."
      }
    }
  ],
  "feedback": [
    {
      "feedback_id": "uuid",
      "category": "Feature Request",
      "message": "...",
      "timestamp": "2026-02-24T14:20:00.000000"
    }
  ],
  "last_login": "2026-02-25T10:30:00.000000",
  "last_logout": "2026-02-25T12:45:00.000000"
}
```

## Support

For issues or questions, contact the development team or check the backend logs in Render dashboard.
