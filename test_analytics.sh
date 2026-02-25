#!/bin/bash

# Test script for analytics endpoints

echo "Testing Weekly Analytics Report..."
echo "=================================="
echo ""

# Test 1: Get weekly report (7 days)
echo "1. Getting 7-day report..."
curl -s "https://neunet-ai-services.onrender.com/api/auth/analytics/weekly-report?days=7" | python3 -m json.tool

echo ""
echo ""

# Test 2: Get monthly report (30 days)
echo "2. Getting 30-day report..."
curl -s "https://neunet-ai-services.onrender.com/api/auth/analytics/weekly-report?days=30" | python3 -m json.tool

echo ""
echo ""

# Test 3: Send email (uncomment and add your email)
# echo "3. Sending email report..."
# curl -X POST "https://neunet-ai-services.onrender.com/api/auth/analytics/send-weekly-report?recipient_email=YOUR_EMAIL@example.com&days=7"

echo ""
echo "Tests complete!"
