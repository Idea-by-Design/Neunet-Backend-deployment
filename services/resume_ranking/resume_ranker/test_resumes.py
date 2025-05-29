import os
import json
import logging
import time
from dotenv import load_dotenv
import sys, os
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
from common.database.cosmos.db_operations import fetch_job_description, fetch_job_description_questionnaire, fetch_resume_with_email

# Set up logging
log_file_path = os.path.join(os.getcwd(), 'resume_ranking.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# # Load environment variables
# load_dotenv()

def rank_resume_for_candidate(job_description_id, candidate_email):
    try:
        # Call DB to fetch Job Description
        job_description = fetch_job_description(job_description_id)
        
        # Call DB to fetch Job Description Questionnaire
        job_description_questionnaire = fetch_job_description_questionnaire(job_description_id)
        questionnaire_id = job_description_questionnaire['id']
        questions = job_description_questionnaire['questionnaire']
        
        # Fetch resume for the candidate
        resume = fetch_resume_with_email(candidate_email)
        
        logging.info(f"Starting resume ranking test for {candidate_email} with job description ID {job_description_id}.")
        result = initiate_chat(job_description_id, questionnaire_id, resume, job_description, candidate_email, questions)
        logging.info(f"Ranking for {candidate_email} completed successfully.")
        
        return result

    except Exception as e:
        logging.error(f"An error occurred for candidate {candidate_email}: {e}")
        return None

def main():
    # Record start time
    start_time = time.time()

    # Specify the job_id to process
    job_id = input("Enter the job_id to rank candidates for: ").strip()

    # Fetch all candidate applications for this job
    from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count
    print(f"[DEBUG] Fetching applications for job_id: {job_id}")
    applications = fetch_top_k_candidates_by_count(job_id, top_k=1000)  # Increase top_k as needed

    if not applications:
        print(f"[DEBUG] No applications found for job_id {job_id}.")
        return

    print(f"[DEBUG] Found {len(applications)} applications for job_id {job_id}")
    for idx, app in enumerate(applications):
        print(f"[DEBUG] Processing application {idx+1}/{len(applications)}: {json.dumps(app, indent=2)}")
        candidate_id = app.get('candidate_id')
        candidate_email = app.get('email')
        # Fallback: use email as candidate_id if candidate_id is missing (for testing only)
        if not candidate_id and candidate_email:
            print(f"[WARNING] candidate_id missing, using candidate_email as candidate_id for testing: {candidate_email}")
            candidate_id = candidate_email
        if not candidate_id:
            print(f"[DEBUG] Skipping: No candidate_id found in application: {app}")
            logging.warning(f"No candidate_id found in application: {app}")
            continue
        if not candidate_email:
            print(f"[DEBUG] Skipping: No candidate_email found in application: {app}")
            logging.warning(f"No candidate_email found in application: {app}")
            continue
        print(f"[DEBUG] Processing candidate_id: {candidate_id}, candidate_email: {candidate_email}")
        try:
            # Call DB to fetch Job Description
            print(f"[DEBUG] Fetching job description for job_id: {job_id}")
            job_description = fetch_job_description(job_id)
            # Call DB to fetch Job Description Questionnaire
            print(f"[DEBUG] Fetching job description questionnaire for job_id: {job_id}")
            job_description_questionnaire = fetch_job_description_questionnaire(job_id)
            questionnaire_id = job_description_questionnaire['id']
            questions = job_description_questionnaire['questionnaire']
            # Fetch resume using candidate_email
            print(f"[DEBUG] Fetching resume for candidate_email: {candidate_email}")
            def dict_resume_to_text(resume_dict):
                if not isinstance(resume_dict, dict):
                    return ""
                parts = []
                for key, value in resume_dict.items():
                    if isinstance(value, (str, int, float)):
                        parts.append(f"{key}: {value}")
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                for k, v in item.items():
                                    parts.append(f"{k}: {v}")
                            else:
                                parts.append(str(item))
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            parts.append(f"{k}: {v}")
                return "\n".join(parts)

            resume_record = fetch_resume_with_email(candidate_email)
            resume = None
            if isinstance(resume_record, dict):
                resume_data = resume_record.get('resume')
                if isinstance(resume_data, dict):
                    resume = dict_resume_to_text(resume_data)
                else:
                    resume = resume_data
            else:
                resume = resume_record

            # Print and log the type and preview of resume
            print(f"[DEBUG] Type of resume for candidate_email {candidate_email}: {type(resume)}")
            if isinstance(resume, str):
                print(f"[DEBUG] Preview of resume: {resume[:200]}...")
                print(f"[DEBUG] Calling initiate_chat for candidate_email {candidate_email}")
            else:
                print("\n==================== WARNING: Resume is NOT a string! ====================")
                print(f"[DEBUG] Resume for candidate_email {candidate_email} is type: {type(resume)}")
                print(f"[DEBUG] Resume value: {repr(resume)}")
                print(f"[DEBUG] Full resume_record for candidate_email {candidate_email}: {resume_record}")
                print("==================== SKIPPING THIS CANDIDATE ====================\n")
                logging.warning(f"Resume for candidate_email {candidate_email} is not a string. Skipping.")
                continue

            # Log and print for traceability
            logging.info(f"Ranking candidate_id: {candidate_id}, candidate_email: {candidate_email} for job_id: {job_id}")
            logging.info(f"Fetched resume for candidate_email {candidate_email}: {resume is not None}")

            # Run the ranking process
            result = initiate_chat(job_id, questionnaire_id, resume, job_description, candidate_email, questions)
            logging.info(f"Ranking for candidate_email {candidate_email} completed successfully. Result: {result}")
        except Exception as e:
            logging.error(f"An error occurred for candidate_id {candidate_id}: {e}")
            continue

    # Record end time
    end_time = time.time()
    total_time = end_time - start_time
    logging.info(f"Total time taken for resume ranking: {total_time:.2f} seconds.")
    print(f"Total time taken for resume ranking: {total_time:.2f} seconds.")

if __name__ == "__main__":
    main()
