import os
import sys
from services.common.database.cosmos import db_operations
from services.resume_ranking.job_description_questionnaire.jd_questionnaire_generator import generate_questionnaire
import datetime

# Load all jobs with valid 6-digit job_id
jobs = db_operations.fetch_all_jobs()
valid_jobs = [j for j in jobs if 'job_id' in j and isinstance(j['job_id'], str) and j['job_id'].isdigit() and len(j['job_id']) == 6]

for job in valid_jobs:
    job_id = job['job_id']
    print(f"Checking job {job_id} - {job.get('title','')}")
    questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
    if questionnaire_doc:
        print(f"  Already has questionnaire. Skipping.")
        continue
    print(f"  No questionnaire found. Generating...")
    try:
        # Generate questionnaire
        questionnaire = generate_questionnaire(job)
        if isinstance(questionnaire, str):
            import json
            questionnaire = json.loads(questionnaire)
        # Attach job_id and unique id
        questionnaire['job_id'] = job_id
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = f"{job_id}_{current_time}"
        questionnaire['id'] = unique_id
        # Store questionnaire
        db_operations.store_job_questionnaire(questionnaire)
        # Attach to job record and upsert
        job['questionnaire'] = questionnaire
        db_operations.upsert_jobDetails(job)
        print(f"  Questionnaire generated and stored for job {job_id}")
    except Exception as e:
        print(f"  [ERROR] Failed for job {job_id}: {e}")

print("Backfill complete.")
