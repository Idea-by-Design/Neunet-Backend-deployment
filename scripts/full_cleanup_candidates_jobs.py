import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from common.database.cosmos.db_operations import containers, config
from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count, fetch_all_jobs

# Remove all candidates where candidate_id is not present
# Remove all applications/candidates where job_id is not present

def full_cleanup():
    # Clean up candidates/applications in application_container
    container = containers[config['database']['application_container_name']]
    query = "SELECT * FROM c"
    docs = list(container.query_items(query=query, enable_cross_partition_query=True))
    to_delete = []
    for doc in docs:
        doc_type = doc.get('type')
        candidate_id = doc.get('candidate_id')
        job_id = doc.get('job_id')
        doc_id = doc.get('id')
        # Remove any application where type != 'candidate'
        if doc_type != 'candidate':
            print(f"[CLEANUP] Will delete non-candidate application: id={doc_id} type={doc_type}")
            to_delete.append((doc_id, job_id))
            continue
        # Remove any candidate where candidate_id is missing/empty or job_id is missing/empty
        if doc_type == 'candidate' and (not candidate_id or not str(candidate_id).strip()):
            print(f"[CLEANUP] Will delete candidate missing/empty candidate_id: id={doc_id} job_id={job_id}")
            to_delete.append((doc_id, job_id))
            continue
        if doc_type == 'candidate' and (not job_id or not str(job_id).strip()):
            print(f"[CLEANUP] Will delete candidate missing/empty job_id: id={doc_id} candidate_id={candidate_id}")
            to_delete.append((doc_id, job_id))
            continue
    # Actually delete
    for doc_id, job_id in to_delete:
        try:
            pk = job_id if job_id else doc_id
            print(f"[CLEANUP] Attempting to delete: id={doc_id}, partition_key={pk}")
            container.delete_item(item=doc_id, partition_key=pk)
            print(f"[CLEANUP] Deleted: {doc_id}")
        except Exception as e:
            print(f"[ERROR] Failed to delete {doc_id} with partition_key={pk}: {e}")

    # Force delete the specific problematic record
    try:
        print("[CLEANUP] Force deleting application id='732231_732231_1747435671', partition_key='732231'")
        container.delete_item(item='732231_732231_1747435671', partition_key='732231')
        print("[CLEANUP] Force deleted: 732231_732231_1747435671")
    except Exception as e:
        print(f"[ERROR] Force delete failed for 732231_732231_1747435671: {e}")

    # Clean up jobs in job_description_container
    job_container = containers[config['database']['job_description_container_name']]
    query = "SELECT * FROM c"
    jobs = list(job_container.query_items(query=query, enable_cross_partition_query=True))
    to_delete_jobs = []
    for job in jobs:
        job_id = job.get('job_id')
        job_doc_id = job.get('id')
        # Remove any job where job_id is missing/empty
        if not job_id or not str(job_id).strip():
            print(f"[CLEANUP] Will delete job missing/empty job_id: id={job_doc_id}")
            to_delete_jobs.append((job_doc_id, job_id))
    for job_doc_id, job_id in to_delete_jobs:
        try:
            pk = job_id if job_id else job_doc_id
            job_container.delete_item(item=job_doc_id, partition_key=pk)
            print(f"[CLEANUP] Deleted job: {job_doc_id}")
        except Exception as e:
            print(f"[ERROR] Failed to delete job {job_doc_id}: {e}")

if __name__ == "__main__":
    full_cleanup()
