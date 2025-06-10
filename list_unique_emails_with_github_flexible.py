from common.database.cosmos.db_operations import ensure_containers
import json

def extract_github_link(resume_obj):
    # Flexible extraction matching frontend logic
    if not resume_obj:
        return None
    # Top-level keys
    for key in ["github", "gitHub", "GitHub"]:
        link = resume_obj.get(key)
        if link:
            return link
    # Nested under links (try both dot and bracket notation)
    links = resume_obj.get("links") or resume_obj.get('links')
    if links and isinstance(links, dict):
        for key in ["gitHub", "github", "GitHub"]:
            link = links.get(key)
            if link:
                return link
    return None

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
        # Try to parse as JSON
        try:
            if isinstance(resume, str):
                resume_obj = json.loads(resume)
            else:
                resume_obj = resume
        except Exception:
            resume_obj = None
        github_link = extract_github_link(resume_obj)
    if email not in unique_github:
        unique_github[email] = github_link

print("Email,Github Link")
for email in sorted(unique_github.keys()):
    print(f"{email},{unique_github[email] if unique_github[email] else ''}")
