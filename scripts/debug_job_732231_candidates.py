import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count

def print_candidates_for_job(job_id):
    print(f"[INFO] Candidates for job_id: {job_id}")
    candidates = fetch_top_k_candidates_by_count(job_id, top_k=1000)
    for cand in candidates:
        print("---")
        for k, v in cand.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    print_candidates_for_job('732231')
