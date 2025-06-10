from common.database.cosmos.db_operations import ensure_containers
import json

containers = ensure_containers()
container = containers['applications']
unique_github = dict()  # email -> github_link (first found)
for item in container.query_items(query="SELECT * FROM c WHERE c.type = 'candidate'", enable_cross_partition_query=True):
    email = item.get('email')
    if not email:
        continue
    resume = item.get('resume')
    github_link = None
    if resume:
        try:
            if isinstance(resume, str):
                resume_json = json.loads(resume)
            else:
                resume_json = resume
            github_link = resume_json.get('links', {}).get('gitHub')
        except Exception:
            pass
    if email not in unique_github:
        unique_github[email] = github_link

print("Email,Github Link")
for email in sorted(unique_github.keys()):
    print(f"{email},{unique_github[email] if unique_github[email] else ''}")
