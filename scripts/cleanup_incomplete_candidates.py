import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count
from common.database.cosmos.db_operations import fetch_all_jobs
from common.database.cosmos.db_operations import containers, config

def cleanup_incomplete_candidates():
    jobs = fetch_all_jobs()
    job_ids = [job['job_id'] for job in jobs if 'job_id' in job]
    to_delete = []
    for job_id in job_ids:
        applications = fetch_top_k_candidates_by_count(job_id, top_k=1000)
        for app in applications:
            candidate_email = app.get('email')
            job_id_app = app.get('job_id')
            resume_blob_name = app.get('resume_blob_name')
            app_type = app.get('type')
            candidate_id = app.get('candidate_id')

            # Remove candidates without candidate_id
            if app_type == 'candidate' and not candidate_id:
                print(f"[CLEANUP] Will delete candidate missing candidate_id: id={app.get('id')} job_id={job_id_app} email={candidate_email}")
                to_delete.append(app.get('id'))
                continue
            # Remove any record (candidate or application) without job_id
            if not job_id_app:
                print(f"[CLEANUP] Will delete record missing job_id: id={app.get('id')} type={app_type} email={candidate_email}")
                to_delete.append(app.get('id'))
                continue
            # Existing logic: Delete incomplete candidate or application
            if (app_type == 'candidate' and (not candidate_email or not resume_blob_name)) or \
               (app_type == 'application' and (not candidate_email or not resume_blob_name)):
                print(f"[CLEANUP] Will delete incomplete or non-candidate application: id={app.get('id')} job_id={job_id_app} email={candidate_email} resume_blob_name={resume_blob_name} type={app_type}")
                to_delete.append(app.get('id'))
    # Actually delete
    for app_id in to_delete:
        try:
            containers[config['database']['application_container_name']].delete_item(item=app_id, partition_key=app_id.split('_')[0])
            print(f"[CLEANUP] Deleted application: {app_id}")
        except Exception as e:
            print(f"[ERROR] Failed to delete application {app_id}: {e}")

if __name__ == "__main__":
    cleanup_incomplete_candidates()
