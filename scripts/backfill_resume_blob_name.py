"""
Script to audit and backfill missing 'resume_blob_name' for candidate records in Cosmos DB.
- Finds all candidate records (type='candidate') missing 'resume_blob_name'.
- Attempts to infer the correct blob name from available data.
- Updates the record using upsert_candidate.
- Logs all changes.

Usage:
    python backfill_resume_blob_name.py
"""
import sys
import os
# Always add the repo root (Neunet-Backend-deployment) to sys.path for flat repo imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import logging
from common.database.cosmos.db_operations import (
    fetch_resume_with_email,
    upsert_candidate
)
from common.utils.config_utils import load_config
from azure.cosmos import CosmosClient

logging.basicConfig(level=logging.INFO)

# Load config and connect to Cosmos DB
config = load_config()
COSMOS_ENDPOINT = config['database']['cosmos_db_uri']
COSMOS_KEY = config['database']['cosmos_db_key']
DATABASE_NAME = config['database']['cosmos_db_name']
APPLICATION_CONTAINER = config['database']['application_container_name']

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(APPLICATION_CONTAINER)

def audit_and_backfill():
    query = "SELECT * FROM c WHERE c.type = 'candidate'"
    candidates = list(container.query_items(query=query, enable_cross_partition_query=True))
    missing = [c for c in candidates if not c.get('resume_blob_name')]
    logging.info(f"Found {len(missing)} candidate records missing 'resume_blob_name'.")
    fixed = 0
    for candidate in missing:
        # Try to infer the blob name. Here, assume it's based on email or id if possible.
        email = candidate.get('email')
        job_id = candidate.get('job_id')
        # Example inference: resume blob name is often <job_id>_<email>.pdf
        if email and job_id:
            inferred_blob_name = f"{job_id}_{email}.pdf"
            candidate['resume_blob_name'] = inferred_blob_name
            upsert_candidate(candidate)
            logging.info(f"Updated candidate {email} for job {job_id} with resume_blob_name: {inferred_blob_name}")
            fixed += 1
        else:
            logging.warning(f"Could not infer blob name for candidate: {candidate.get('id')}")
    logging.info(f"Backfill complete. {fixed} records updated.")

if __name__ == "__main__":
    audit_and_backfill()
