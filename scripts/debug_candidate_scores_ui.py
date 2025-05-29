import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from common.database.cosmos.db_operations import fetch_candidate_rankings, fetch_job_description, fetch_top_k_candidates_by_count

def print_candidate_scores_for_all_jobs():
    from common.database.cosmos.db_operations import fetch_all_jobs
    jobs = fetch_all_jobs()
    for job in jobs:
        job_id = job.get('job_id')
        if not job_id:
            continue
        print(f"\n[JOB] {job_id}: {job.get('title', job_id)}")
        rankings = fetch_candidate_rankings(job_id)
        applications = fetch_top_k_candidates_by_count(job_id, top_k=1000)
        for app in applications:
            email = app.get('email')
            name = app.get('name', '-')
            score = rankings.get(email, {}).get('ranking', 'NO SCORE')
            print(f"Candidate: {name} | Email: {email} | Score: {score}")

if __name__ == "__main__":
    print_candidate_scores_for_all_jobs()
