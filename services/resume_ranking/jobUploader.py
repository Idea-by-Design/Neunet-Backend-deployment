import os
import yaml
import json
from common.database.cosmos.db_setup import setup_database
from common.database.cosmos.db_operations import upsert_jobDetails,fetch_job_description
from services.resume_parser.parser.openai_resume_parser import parse_resume_json
from services.resume_parser.parser.doc_parser import parse_doc
from services.resume_parser.parser.pdf_parser import parse_pdf

def main(file_path):
    
       
    # Upsert resume data to the database
    try:
        upsert_jobDetails(file_path)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # file_path = 'test string for job description'
    import json
   
    
    # Check if the job already exists
    existing_job = fetch_job_description('00001')
    print(existing_job)
    x =  '{ "id":"00001", "jd":"test"}'
    file_path = json.loads(x)
    main(file_path)
