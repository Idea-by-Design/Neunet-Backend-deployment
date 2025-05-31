import os
import sys
from pathlib import Path

# Ensure 'services' is a top-level package when running from the project root
import sys, os
sys.path.insert(0, os.path.abspath("."))

import json
from dotenv import load_dotenv
from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
from common.database.cosmos.db_operations import fetch_job_description, fetch_job_description_questionnaire, fetch_resume_with_email
import datetime
# Load environment variables
# Always load .env from backend root
backend_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(backend_root / ".env")



        
        
def main():
    
    
    # Call DB to fetch Job Description
    job_description_id = 996137
    job_description = fetch_job_description(job_description_id)
    # print("Job Description: \n", job_description)
    
    # Call DB to fetch Job Description Questionnaire
    job_description_questionnaire = fetch_job_description_questionnaire(job_description_id)
    questionnaire_id = job_description_questionnaire['id']
    questions = job_description_questionnaire['questionnaire']
    # print("Job Description Questionnaire: \n", questions)

    
    # resume_path = r"services\resume_ranking\test_data\sample_files\sample_resume_1.txt"
    # resume = f"""{read_file_to_string(resume_path)}"""
    # candidate_email= "john.doe@example.com"
    
    
    candidate_email= "cynthia@beamjobs.com"
    resume_record = fetch_resume_with_email(candidate_email)
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
    resume = None
    import json as _json
    if isinstance(resume_record, dict):
        resume_data = resume_record.get('resume')
        # If resume_data is a dict, flatten it
        if isinstance(resume_data, dict):
            resume = dict_resume_to_text(resume_data)
        # If resume_data is a JSON string, parse and flatten
        elif isinstance(resume_data, str):
            try:
                parsed = _json.loads(resume_data)
                if isinstance(parsed, dict):
                    resume = dict_resume_to_text(parsed)
                else:
                    resume = str(parsed)
            except Exception:
                resume = resume_data
        else:
            resume = str(resume_data)
    else:
        resume = str(resume_record)

    print("Starting resume ranking test...")
    result = initiate_chat(job_description_id, questionnaire_id, resume, job_description, candidate_email, questions)
    print(f"Ranking for {candidate_email} completed successfully.")
    return result

if __name__ == "__main__":
    main()