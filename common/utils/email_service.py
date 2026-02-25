import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def format_analytics_report_html(report_data):
    """
    Format the analytics report as HTML email.
    """
    summary = report_data.get('summary', {})
    users = report_data.get('users', [])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                border-radius: 8px;
                padding: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #7C3AED;
                border-bottom: 3px solid #7C3AED;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #6D28D9;
                margin-top: 30px;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 36px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .stat-label {{
                font-size: 14px;
                opacity: 0.9;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th {{
                background-color: #7C3AED;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
            }}
            tr:hover {{
                background-color: #f9fafb;
            }}
            .user-section {{
                margin: 30px 0;
                padding: 20px;
                background-color: #f9fafb;
                border-radius: 8px;
                border-left: 4px solid #7C3AED;
            }}
            .feedback-item {{
                background-color: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 6px;
                border-left: 3px solid #10b981;
            }}
            .activity-item {{
                display: inline-block;
                padding: 5px 10px;
                margin: 5px;
                background-color: #ddd6fe;
                color: #5b21b6;
                border-radius: 4px;
                font-size: 12px;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                text-align: center;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Neunet Weekly Analytics Report</h1>
            <p><strong>Report Period:</strong> {report_data.get('period', 'N/A')}</p>
            <p><strong>Generated:</strong> {datetime.fromisoformat(report_data.get('report_generated', '')).strftime('%B %d, %Y at %I:%M %p UTC')}</p>
            
            <h2>Summary</h2>
            <div class="summary-grid">
                <div class="stat-card">
                    <div class="stat-label">Active Users</div>
                    <div class="stat-value">{summary.get('active_users', 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Logins</div>
                    <div class="stat-value">{summary.get('total_logins', 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Feedback</div>
                    <div class="stat-value">{summary.get('total_feedback', 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Hours Spent</div>
                    <div class="stat-value">{summary.get('total_hours_spent', 0)}</div>
                </div>
            </div>
            
            <h2>User Activity Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Email</th>
                        <th>Logins</th>
                        <th>Hours</th>
                        <th>Feedback</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for user in users:
        stats = user.get('session_stats', {})
        html += f"""
                    <tr>
                        <td><strong>{user.get('name', 'N/A')}</strong></td>
                        <td>{user.get('email', 'N/A')}</td>
                        <td>{stats.get('total_logins', 0)}</td>
                        <td>{stats.get('total_time_hours', 0)}</td>
                        <td>{stats.get('total_feedback', 0)}</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
    """
    
    # Add detailed user sections
    for user in users:
        if user.get('feedback_in_period') or user.get('activity_in_period'):
            html += f"""
            <div class="user-section">
                <h3>{user.get('name', 'N/A')} ({user.get('email', 'N/A')})</h3>
                <p><strong>Company Size:</strong> {user.get('company_size', 'N/A')}</p>
                <p><strong>Last Login:</strong> {user.get('last_login', 'N/A')}</p>
            """
            
            # Show feedback
            if user.get('feedback_in_period'):
                html += "<h4>Feedback:</h4>"
                for feedback in user.get('feedback_in_period', []):
                    html += f"""
                    <div class="feedback-item">
                        <strong>{feedback.get('category', 'General')}</strong><br>
                        {feedback.get('message', 'N/A')}<br>
                        <small>{datetime.fromisoformat(feedback.get('timestamp', '')).strftime('%B %d, %Y at %I:%M %p')}</small>
                    </div>
                    """
            
            # Show activity summary
            if user.get('activity_in_period'):
                html += f"""
                <h4>Activity Summary:</h4>
                <p>
                    <span class="activity-item">🔑 {user.get('session_stats', {}).get('total_logins', 0)} logins</span>
                    <span class="activity-item">⏱️ {user.get('session_stats', {}).get('total_time_hours', 0)} hours</span>
                    <span class="activity-item">⏰ Avg session: {user.get('session_stats', {}).get('average_session_minutes', 0)} min</span>
                </p>
                """
            
            html += "</div>"
    
    html += """
            <div class="footer">
                <p>This is an automated weekly report from Neunet Analytics</p>
                <p>© 2026 Neunet - AI-Powered Hiring Platform</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def send_analytics_email(report_data, recipient_email):
    """
    Send analytics report via email.
    
    Args:
        report_data: The analytics report dictionary
        recipient_email: Email address to send the report to
    """
    try:
        # Email configuration from environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        
        if not sender_email or not sender_password:
            print("Error: Email credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Neunet Weekly Analytics Report - {report_data.get('period', 'N/A')}"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # Create HTML content
        html_content = format_analytics_report_html(report_data)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"Analytics report sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
