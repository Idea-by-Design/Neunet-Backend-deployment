import os
import yaml
import json
import time  # Import the time module for adding sleep
from common.database.cosmos.db_setup import setup_database
from common.database.cosmos.db_operations import upsert_resume
from services.resume_parser.parser.openai_resume_parser import parse_resume_json
from services.resume_parser.parser.doc_parser import parse_doc
from services.resume_parser.parser.pdf_parser import parse_pdf

def process_resume(file_path):
    """
    Process a single resume file (PDF, DOC, DOCX) and upload the parsed data to the database.
    """
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == '.pdf':
        text, hyperlinks = parse_pdf(file_path)
    elif file_extension in ['.doc', '.docx']:
        text, hyperlinks = parse_doc(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    extracted_info = parse_resume_json(text, hyperlinks)
    
    extracted_info['id'] = extracted_info['email']

    return extracted_info

def main(directory_path, delay_seconds=1):
    """
    Main function to process all resume files in the directory with an optional delay between API calls.
    
    Args:
        directory_path (str): Path to the directory containing resumes.
        delay_seconds (int): Time in seconds to wait between processing each file.
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"No such directory: '{directory_path}'")

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

    # Walk through the directory and process all files
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                extracted_info = process_resume(file_path)
                # Upsert resume data to the database
                upsert_resume(container, extracted_info)
                print(f"Successfully processed and uploaded: {file_path}")

                # Sleep for the specified delay to prevent too frequent API calls
                time.sleep(delay_seconds)

            except Exception as e:
                print(f"Failed to process {file_path}: {e}")

if __name__ == "__main__":
    directory_path = 'C:\\Users\\akalps\\Downloads\\Job Descriptions + Resumes'
    delay_seconds = 2  # Set delay between API calls to 2 seconds
    main(directory_path, delay_seconds)
