
from common.database.cosmos.db_operations import fetch_candidates_with_github_links, upsert_github_analysis
from services.github_analysis.analyze_github import analyze_github_profile


# Fetch candidates with GitHub links from Cosmos DB
candidates = fetch_candidates_with_github_links()
print(f"Fetched {len(candidates)} candidates.")

from urllib.parse import urlparse

def extract_github_username(github_link):
    if github_link:
        path = urlparse(github_link).path
        username = path.strip('/').split('/')[0]
        return username
    return github_link

processed_emails = set()
processed_candidates = []
for candidate in candidates:
    github_identifier = candidate['github']  # Could be a full URL or a username
    email = candidate['email']

    if not github_identifier:
        print(f"No GitHub identifier found for {email}")
        continue
    if email in processed_emails:
        print(f"Skipping duplicate candidate: {email}")
        continue
    processed_emails.add(email)
    processed_candidates.append(email)

    username = extract_github_username(github_identifier)
    print(f"Analyzing GitHub profile for {email} (GitHub: {username})")
    print(f"[DEBUG] Calling analyze_github_profile for {email}")
    analysis_data = analyze_github_profile(username, email)
    print(f"[DEBUG] Finished analyze_github_profile for {email}")
    analysis_data['email'] = email
    analysis_data['id'] = email
    print(f"[DEBUG] About to upsert GitHub analysis for {email}")
    upsert_github_analysis(email, github_identifier, analysis_data)
    print(f"[DEBUG] Finished upserting GitHub analysis for {email}")

print("Script execution completed.")
print("\n[SUMMARY] GitHub analysis attempted for the following candidates:")
for cand in processed_candidates:
    print(f" - {cand}")