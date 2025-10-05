#!/usr/bin/env python3
"""
Script to run GitHub analysis for all candidates with GitHub links.
Requires GITHUB_TOKEN in .env file.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Verify GITHUB_TOKEN
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("[ERROR] GITHUB_TOKEN not found in .env file")
    print("Please add your GitHub personal access token to .env:")
    print("  GITHUB_TOKEN=your_token_here")
    sys.exit(1)

print(f"[INFO] GITHUB_TOKEN found (length: {len(GITHUB_TOKEN)})")

# Import after env is loaded
from common.database.cosmos.db_operations import fetch_candidates_with_github_links, upsert_github_analysis
from services.github_analysis.analyze_github import analyze_github_profile
from urllib.parse import urlparse

def extract_github_username(github_link):
    """Extract username from GitHub URL or return as-is if already a username."""
    if github_link:
        path = urlparse(github_link).path
        username = path.strip('/').split('/')[0]
        return username
    return github_link

# Fetch candidates with GitHub links
print("[INFO] Fetching candidates with GitHub links...")
candidates = fetch_candidates_with_github_links()
print(f"[INFO] Found {len(candidates)} candidates with GitHub links")

if not candidates:
    print("[WARNING] No candidates with GitHub links found in database")
    print("Make sure candidates have parsed_resume.links.github or parsed_resume.github populated")
    sys.exit(0)

# Process each candidate
processed_emails = set()
processed_candidates = []

for candidate in candidates:
    github_identifier = candidate['github']
    email = candidate['email']

    if not github_identifier:
        print(f"[SKIP] No GitHub identifier found for {email}")
        continue
    
    if email in processed_emails:
        print(f"[SKIP] Duplicate candidate: {email}")
        continue
    
    processed_emails.add(email)
    processed_candidates.append(email)

    username = extract_github_username(github_identifier)
    print(f"\n[PROCESSING] {email} (GitHub: {username})")
    
    try:
        print(f"  → Analyzing GitHub profile...")
        analysis_data = analyze_github_profile(username, email)
        
        # Add metadata
        analysis_data['email'] = email
        
        print(f"  → Upserting to database...")
        upsert_github_analysis(email, username, analysis_data)
        
        print(f"  ✓ Successfully processed {email}")
        print(f"    - Repositories: {analysis_data.get('total_repositories', 0)}")
        print(f"    - Commits: {analysis_data.get('total_commits', 0)}")
        
    except Exception as e:
        print(f"  ✗ Error processing {email}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("GitHub Analysis Complete")
print("="*60)
print(f"Total candidates processed: {len(processed_candidates)}")
print("\nProcessed candidates:")
for cand in processed_candidates:
    print(f"  - {cand}")
