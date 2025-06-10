"""
End-of-day GitHub analysis script.
- Scans all candidate applications.
- Extracts GitHub links from both resume JSON and raw text.
- For each candidate with a GitHub link:
    - If a github_analysis record exists for (email, github_username) and is <6 months old, skip.
    - If not, or if older than 6 months, run GitHub analysis and update the record.
- Logs all actions and outputs a summary.
"""
import json
import re
from datetime import datetime, timedelta
from common.database.cosmos.db_operations import ensure_containers, fetch_github_analysis_by_candidate, upsert_github_analysis
from services.github_analysis.analyze_github import analyze_github_profile

def extract_github_link(resume):
    """Extract GitHub link from resume JSON or raw text."""
    if not resume:
        return None
    github = None
    # Try JSON parsing if not already dict
    resume_json = None
    if isinstance(resume, dict):
        resume_json = resume
    else:
        try:
            resume_json = json.loads(resume)
        except Exception:
            resume_json = None
    # Flexible extraction from JSON
    if resume_json:
        github = (
            resume_json.get('github') or resume_json.get('gitHub') or resume_json.get('GitHub') or
            (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('github') or
            (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('gitHub') or
            (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('GitHub')
        )
        if github:
            return github
    # Fallback: extract from raw text
    text = resume if isinstance(resume, str) else json.dumps(resume_json or {})
    github_regex = r"https?://(?:www\\.)?github\\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?"
    matches = re.findall(github_regex, text)
    return matches[0] if matches else None

def extract_github_username(github_url):
    if not github_url:
        return None
    # Ignore github.io or github pages
    if 'github.io' in github_url:
        return None
    # Normalize to ensure scheme for regex
    if not github_url.startswith('http'):
        github_url = 'https://' + github_url
    # Regex: match scheme (optional www), github.com, then capture username (no slash after)
    match = re.match(r"https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)(?:/)?", github_url)
    return match.group(1) if match else None

def is_analysis_recent(analysis_doc):
    if not analysis_doc or not analysis_doc.get('created_at'):
        return False
    try:
        created_at = datetime.fromisoformat(analysis_doc['created_at'].replace('Z', '+00:00'))
        return (datetime.utcnow() - created_at) < timedelta(days=180)
    except Exception:
        return False

def main():
    containers = ensure_containers()
    container = containers['applications']
    # Fetch all application documents
    candidates = list(container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True))
    analyzed, skipped, failed = 0, 0, 0
    summary = []
    processed_emails = set()
    for cand in candidates:
        email = cand.get('email')
        candidate_id = cand.get('candidate_id')
        cand_type = cand.get('type')
        parsed_resume = cand.get('parsed_resume')
        resume = cand.get('resume')
        # Only process if type == 'candidate' and email or candidate_id is present
        if cand_type != 'candidate' or (not email and not candidate_id):
            continue
        # Only process each email once
        if email in processed_emails:
            continue
        # Prefer parsed_resume, fallback to resume
        github_url, source = None, None
        if parsed_resume:
            github_url = extract_github_link(parsed_resume)
            if github_url:
                source = 'parsed_resume'
        if not github_url and resume:
            github_url = extract_github_link(resume)
            if github_url:
                source = 'resume'
        if not github_url:
            continue
        summary.append({
            'email': email,
            'candidate_id': candidate_id,
            'github_url': github_url,
            'source': source
        })
        github_username = extract_github_username(github_url)
        print(f"[DEBUG] Candidate: {email or candidate_id} | GitHub URL: {github_url} | Extracted Username: {github_username}")
        if not github_username:
            print(f"[WARN] Could not extract username from {github_url} for {email or candidate_id}")
            continue
        # Recency check: only analyze if missing or stale
        analysis_doc = fetch_github_analysis_by_candidate(email, github_username, return_full_item=True)
        recent = is_analysis_recent(analysis_doc)
        print(f"[DEBUG] Analysis recent for {email or candidate_id} ({github_username}): {recent}")
        if recent:
            skipped += 1
            print(f"[SKIP] Recent analysis exists for {email or candidate_id} ({github_username})")
            processed_emails.add(email)
            continue
        try:
            print(f"[ANALYZE] Running GitHub analysis for {email or candidate_id} ({github_username})...")
            analysis_result = analyze_github_profile(github_username, email)
            upsert_github_analysis(email, github_username, analysis_result)
            analyzed += 1
            print(f"[DONE] Analysis complete for {email or candidate_id} ({github_username})")
            processed_emails.add(email)
        except Exception as e:
            failed += 1
            print(f"[FAIL] Analysis failed for {email or candidate_id} ({github_username}): {e}")
    print("\n=== GitHub Link Extraction Summary ===")
    for entry in summary:
        print(f"Candidate: {entry['email'] or entry['candidate_id']} | GitHub: {entry['github_url']} | Source: {entry['source']}")
    print(f"Total candidates with GitHub links: {len(summary)}")
    print("\n=== End-of-Day GitHub Analysis Summary ===")
    print(f"Analyzed: {analyzed}")
    print(f"Skipped (recent): {skipped}")
    print(f"Failed: {failed}")
    print("=== Done ===")

if __name__ == "__main__":
    main()
