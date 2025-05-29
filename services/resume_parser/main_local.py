import os
import yaml
import json
from common.database.cosmos.db_setup import setup_database
from common.database.cosmos.db_operations import upsert_resume
from services.resume_parser.parser.openai_resume_parser import parse_resume_json
from services.resume_parser.parser.doc_parser import parse_doc
from services.resume_parser.parser.pdf_parser import parse_pdf

def main(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No such file: '{file_path}'")

    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == '.pdf':
        text, hyperlinks = parse_pdf(file_path)
    elif file_extension in ['.doc', '.docx']:
        text, hyperlinks = parse_doc(file_path)
    else:
        raise ValueError("Unsupported file format")

    extracted_info = parse_resume_json(text, hyperlinks)
    
    extracted_info['id'] = extracted_info['email']

    # Load database configuration
    with open("config/config.yaml", 'r') as file:
        config = yaml.safe_load(file)
    
    # Setup database connection
    _, container = setup_database(
        config['database']['cosmos_db_uri'],
        config['database']['cosmos_db_key'],
        config['database']['cosmos_db_name'],
        config['database']['resumes_container_name']
    )
    
    # Upsert resume data to the database
    try:
        upsert_resume(container, extracted_info)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    file_path = 'D:\Hemant_Singh_Resume.pdf'
    main(file_path)
