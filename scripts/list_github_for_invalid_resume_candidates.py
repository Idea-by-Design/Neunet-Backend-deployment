"""
For candidates whose resume field is not valid JSON, try to extract GitHub links directly from the raw resume string using substring and regex methods.
This script targets the 9 candidates (from your previous investigations) and prints any GitHub links found in their resumes.
"""
import re
from common.database.cosmos.db_operations import ensure_containers

def extract_github_links_from_text(text):
    if not text or not isinstance(text, str):
        return []
    # Simple regex to match GitHub URLs
    github_regex = r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?"
    return re.findall(github_regex, text)

def main():
    # List of emails/job_ids for the 9 candidates you want to check
    target_candidates = [
        # Fill this list with the actual (email, job_id) tuples for the 9 candidates
        # Example:
        # ("user@example.com", "123456"),
    ]
    containers = ensure_containers()
    container = containers['applications']
    for email, job_id in target_candidates:
        query = f"SELECT * FROM c WHERE c.type = 'candidate' AND c.email = '{email}' AND c.job_id = '{job_id}'"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            print(f"No record for {email} job {job_id}")
            continue
        item = items[0]
        resume = item.get('resume')
        if not resume:
            print(f"No resume for {email} job {job_id}")
            continue
        if isinstance(resume, dict):
            print(f"Resume for {email} job {job_id} is valid JSON, skipping.")
            continue
        # Try to extract GitHub links from raw text
        links = extract_github_links_from_text(resume)
        print(f"{email} job {job_id}: {links if links else 'No GitHub link found'}")

if __name__ == "__main__":
    main()
