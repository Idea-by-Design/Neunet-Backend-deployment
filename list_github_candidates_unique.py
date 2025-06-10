from common.database.cosmos.db_operations import ensure_containers
import json
from urllib.parse import urlparse

containers = ensure_containers()
container = containers['applications']
github_candidates = dict()  # email -> (username, link)
for item in container.query_items(query="SELECT * FROM c WHERE c.type = 'candidate'", enable_cross_partition_query=True):
    email = item.get('email')
    resume = item.get('resume')
    if not email or not resume:
        continue
    try:
        if isinstance(resume, str):
            resume_json = json.loads(resume)
        else:
            resume_json = resume
        github_link = resume_json.get('links', {}).get('gitHub')
        if github_link:
            # Extract username if possible
            path = urlparse(github_link).path
            username = path.strip('/').split('/')[0] if 'github.com' in github_link else ''
            github_candidates[email] = (username, github_link)
    except Exception as e:
        print(f"Error parsing resume for {email}: {e}")

print("Email, GitHub Username, GitHub Link:")
for email, (username, link) in github_candidates.items():
    print(f"{email}, {username}, {link}")
print(f"\nTotal unique candidates with GitHub links: {len(github_candidates)}")
