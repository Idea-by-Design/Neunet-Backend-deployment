import sys
import os
import json
# Ensure neunet_ai_services is in sys.path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from services.resume_ranking.resume_ranker.rank_on_application import rank_candidate_on_application
from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count

from common.database.cosmos.db_operations import fetch_all_jobs

def rank_all_applications_for_all_jobs():
    jobs = fetch_all_jobs()
    job_ids = [job['job_id'] for job in jobs if 'job_id' in job]
    print(f"[INFO] Found {len(job_ids)} unique job_ids.")
    total_ranked = 0
    total_skipped = 0
    for job_idx, job_id in enumerate(job_ids):
        print(f"\n[INFO] Processing job_id {job_id} ({job_idx+1}/{len(job_ids)})")
        applications = fetch_top_k_candidates_by_count(job_id, top_k=1000)
        ranked = 0
        skipped = 0
        for idx, app in enumerate(applications):
            candidate_email = app.get('email')
            job_id_app = app.get('job_id')
            resume_blob_name = app.get('resume_blob_name')
            if not candidate_email or not job_id_app:
                print(f"[WARNING] Skipping application {app.get('id')} (missing candidate_email or job_id)")
                skipped += 1
                continue
            if not resume_blob_name:
                print(f"[WARNING] Skipping candidate {candidate_email} for job {job_id} (no resume_blob_name, likely incomplete application)")
                skipped += 1
                continue
            try:
                print(f"[INFO] Ranking candidate {candidate_email} for job {job_id} ({idx+1}/{len(applications)})")
                rank_candidate_on_application(job_id, candidate_email)
                ranked += 1
            except Exception as e:
                print(f"[ERROR] Failed to rank candidate {candidate_email}: {e}")
                skipped += 1
        print(f"[INFO] Ranking complete for job_id {job_id}. Total ranked: {ranked}, Skipped: {skipped}")
        total_ranked += ranked
        total_skipped += skipped
    print(f"\n[INFO] All jobs processed. Total ranked: {total_ranked}, Total skipped: {total_skipped}")

if __name__ == "__main__":
    rank_all_applications_for_all_jobs()
