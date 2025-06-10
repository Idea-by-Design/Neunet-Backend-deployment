from common.database.cosmos.db_operations import ensure_containers
import json
from urllib.parse import urlparse

def extract_github_username(github_link):
    if github_link:
        path = urlparse(github_link).path
        username = path.strip('/').split('/')[0]
        return username
    return github_link

containers = ensure_containers()
container = containers['applications']
github_candidates = []
for item in container.query_items(query="SELECT * FROM c WHERE c.type = 'candidate'", enable_cross_partition_query=True):
    email = item.get('email')
    resume = item.get('resume')
    if resume:
        try:
            if isinstance(resume, str):
                resume_json = json.loads(resume)
            else:
                resume_json = resume
            github_link = resume_json.get('links', {}).get('gitHub')
            if github_link:
                username = extract_github_username(github_link)
                github_candidates.append((email, username, github_link))
        except Exception as e:
            print(f"Error parsing resume for {email}: {e}")

print("Email, GitHub Username, GitHub Link:")
for email, username, link in github_candidates:
    print(f"{email}, {username}, {link}")
