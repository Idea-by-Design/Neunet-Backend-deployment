"""
Script to ensure every job in the database has a questionnaire. For each job_id, if a questionnaire is missing, it will be generated and stored.
"""
import os
import sys
import time
from dotenv import load_dotenv

# Add project root and correct service directory to sys.path for absolute imports to work
project_root = os.path.dirname(os.path.abspath(__file__))
# Add the parent directory of neunet_ai_services to sys.path
sys.path.append(project_root)

# Load .env from the correct directory (underscore, not hyphen!)
load_dotenv(dotenv_path=os.path.join(project_root, 'neunet_ai_services', '.env'))

from common.database.cosmos import db_operations
from services.resume_ranking.job_description_questionnaire.jd_questionnaire_generator import generate_questionnaire
import json

load_dotenv(dotenv_path=".env")

def main():
    jobs = db_operations.fetch_all_jobs()
    print(f"Found {len(jobs)} jobs in the database.")
    missing = 0
    for job in jobs:
        job_id = job.get('job_id') or job.get('id')
        if not job_id:
            print(f"[WARN] Job missing job_id: {job}")
            continue
        # Check if questionnaire exists
        questionnaire = db_operations.fetch_job_description_questionnaire(job_id)
        if questionnaire:
            print(f"[OK] Questionnaire already exists for job_id {job_id}")
            continue
        print(f"[INFO] Generating questionnaire for job_id {job_id}")
        jd = db_operations.fetch_job_description(job_id)
        if not jd:
            print(f"[WARN] No job description found for job_id {job_id}")
            continue
        try:
            raw_response = generate_questionnaire(jd)
            # Try to extract JSON object from response
            start_idx = raw_response.find("{")
            end_idx = raw_response.rfind("}")
            json_data = json.loads(raw_response[start_idx:end_idx+1])
            json_data['job_id'] = job_id
            # Unique id for questionnaire
            unique_id = f"{job_id}_{int(time.time())}"
            json_data['id'] = unique_id
            db_operations.store_job_questionnaire(json_data)
            print(f"[SUCCESS] Questionnaire generated and stored for job_id {job_id}")
            missing += 1
        except Exception as e:
            print(f"[ERROR] Failed to generate/store questionnaire for job_id {job_id}: {e}")
    print(f"Done. {missing} questionnaires generated for missing jobs.")

if __name__ == "__main__":
    main()
