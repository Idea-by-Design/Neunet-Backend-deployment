import sys, os
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from common.database.cosmos.db_operations import containers, config

def show_candidate_rankings(job_id):
    # Find the ranking document for this job_id
    query = f"SELECT * FROM c WHERE c.job_id = '{job_id}'"
    results = list(containers[config['database']['ranking_container_name']].query_items(query=query, enable_cross_partition_query=True))
    if not results:
        print(f"No ranking document found for job_id {job_id}.")
        return
    doc = results[0]
    candidates = doc.get('candidates', [])
    if not candidates:
        print(f"No candidates ranked for job_id {job_id}.")
        return
    print(f"Rankings for job_id {job_id}:")
    for c in candidates:
        print(f"Email: {c.get('email')}, Ranking: {c.get('ranking')}, Status: {c.get('application_status')}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id", help="Job ID to show candidate rankings for")
    args = parser.parse_args()
    show_candidate_rankings(args.job_id)
