
from common.database.cosmos.db_operations import fetch_candidates_with_github_links, store_github_analysis
from services.github_analysis.analyze_github import analyze_github_profile


# Fetch candidates with GitHub links from Cosmos DB
candidates = fetch_candidates_with_github_links()
print(f"Fetched {len(candidates)} candidates.")

for candidate in candidates:
    github_identifier = candidate['github']  # Could be a full URL or a username
    email = candidate['email']
    
    if github_identifier:
        print(f"Analyzing GitHub profile for {email}")
        analysis_data = analyze_github_profile(github_identifier, email)
        analysis_data['email'] = email
        analysis_data['id'] = email
        store_github_analysis(analysis_data)
    else:
        print(f"No GitHub identifier found for {email}")

print("Script execution completed.")