import logging
import yaml
import os
import azure.functions as func
from common.database.cosmos.db_setup import setup_database
from common.database.cosmos.db_operations import upsert_resume
from services.resume_parser.parser.openai_resume_parser import parse_resume_json
from services.resume_parser.parser.doc_parser import parse_doc
from services.resume_parser.parser.pdf_parser import parse_pdf

def main(blob: func.InputStream):
    logging.info(f"Processing blob\nName: {blob.name}\nSize: {blob.length} bytes")

    # Save the uploaded blob locally for processing
    local_path = "/tmp/" + os.path.basename(blob.name)
    with open(local_path, "wb") as f:
        f.write(blob.read())

    # Determine the file type and parse accordingly
    file_extension = os.path.splitext(local_path)[1].lower()

    if file_extension == '.pdf':
        text, hyperlinks = parse_pdf(local_path)
    elif file_extension in ['.doc', '.docx']:
        text, hyperlinks = parse_doc(local_path)
    else:
        logging.error("Unsupported file format")
        return

    # Extract resume information using OpenAI
    extracted_info = parse_resume_json(text, hyperlinks)
    extracted_info['id'] = extracted_info.get('email', 'unknown')

    # Load database configuration
    config_path = os.path.join(os.getenv("HOME"), "config/config.yaml")
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    # Setup Cosmos DB connection
    _, container = setup_database(
        config['database']['cosmos_db_uri'],
        config['database']['cosmos_db_key'],
        config['database']['cosmos_db_name'],
        config['database']['container_name']
    )

    # Upsert resume data to the database
    try:
        upsert_resume(container, extracted_info)
        logging.info("Resume data upserted successfully")
    except Exception as e:
        logging.error(f"An error occurred while upserting resume data: {e}")

    # Clean up local file
    os.remove(local_path)
