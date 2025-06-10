"""
Audit candidate records for missing/malformed resume_blob_name, resume field, and social links (GitHub/LinkedIn).
Outputs a summary of affected candidates and highlights issues that may cause frontend UI bugs.
"""
import json
import logging
from common.database.cosmos.db_operations import ensure_containers

def extract_social_links(resume_json):
    github = linkedin = None
    if not resume_json:
        return github, linkedin
    # Flexible extraction matching frontend logic
    github = (
        resume_json.get('github') or resume_json.get('gitHub') or resume_json.get('GitHub') or
        (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('github') or
        (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('gitHub') or
        (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('GitHub')
    )
    linkedin = (
        resume_json.get('linkedin') or resume_json.get('linkedIn') or resume_json.get('LinkedIn') or
        (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('linkedin') or
        (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('linkedIn') or
        (resume_json.get('links', {}) or resume_json.get('links') or resume_json.get('Links', {})).get('LinkedIn')
    )
    return github, linkedin

def audit_candidates():
    containers = ensure_containers()
    container = containers['applications']
    missing_blob = []
    missing_resume = []
    missing_social = []
    all_candidates = list(container.query_items(query="SELECT * FROM c WHERE c.type = 'candidate'", enable_cross_partition_query=True))
    for cand in all_candidates:
        email = cand.get('email')
        job_id = cand.get('job_id')
        cid = cand.get('candidate_id')
        blob = cand.get('resume_blob_name')
        resume = cand.get('resume')
        # Check for missing blob name
        if not blob:
            missing_blob.append({'email': email, 'job_id': job_id, 'candidate_id': cid})
        # Check for missing or malformed resume
        resume_json = None
        if not resume:
            missing_resume.append({'email': email, 'job_id': job_id, 'candidate_id': cid})
        else:
            try:
                resume_json = resume if isinstance(resume, dict) else json.loads(resume)
            except Exception:
                missing_resume.append({'email': email, 'job_id': job_id, 'candidate_id': cid, 'reason': 'resume not valid JSON'})
        # Check for missing social links
        if resume_json:
            github, linkedin = extract_social_links(resume_json)
            if not github and not linkedin:
                missing_social.append({'email': email, 'job_id': job_id, 'candidate_id': cid})
    print("\n=== Candidates missing resume_blob_name ===")
    for c in missing_blob:
        print(c)
    print(f"Total: {len(missing_blob)}\n")
    print("=== Candidates missing resume or invalid resume JSON ===")
    for c in missing_resume:
        print(c)
    print(f"Total: {len(missing_resume)}\n")
    print("=== Candidates missing BOTH GitHub and LinkedIn links in resume ===")
    for c in missing_social:
        print(c)
    print(f"Total: {len(missing_social)}\n")
    print("=== Audit complete ===")

if __name__ == "__main__":
    audit_candidates()
