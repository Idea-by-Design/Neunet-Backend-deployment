from common.database.cosmos.db_operations import ensure_containers
import json

containers = ensure_containers()
print('Containers:', list(containers.keys()))
for name, container in containers.items():
    print(f"\nContainer: {name}")
    count = 0
    candidate_count = 0
    github_count = 0
    for item in container.query_items(query='SELECT * FROM c', enable_cross_partition_query=True):
        count += 1
        if item.get('type') == 'candidate':
            candidate_count += 1
            # Check for GitHub link in resume
            resume = item.get('resume')
            if resume:
                try:
                    if isinstance(resume, str):
                        resume_json = json.loads(resume)
                    else:
                        resume_json = resume
                    github = resume_json.get('links', {}).get('gitHub')
                    if github:
                        github_count += 1
                except Exception as e:
                    print(f"Error parsing resume for {item.get('email')}: {e}")
    print(f"  Total docs: {count}")
    print(f"  Candidates (type='candidate'): {candidate_count}")
    print(f"  Candidates with GitHub link: {github_count}")
