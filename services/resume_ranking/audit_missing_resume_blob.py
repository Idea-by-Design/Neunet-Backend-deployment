import logging
from neunet_ai_services.common.database.cosmos.db_operations import containers, config
from azure.cosmos import exceptions

def audit_candidates_missing_resume_blob():
    """
    Audits candidate records in the application container for missing resume_blob_name.
    Logs and prints all candidates with resume_uploaded=True and missing resume_blob_name.
    """
    application_container = containers[config['database']['application_container_name']]
    query = """
    SELECT c.id, c.email, c.job_id, c.resume_uploaded, c.resume_blob_name
    FROM c
    WHERE c.type = 'candidate'
    """
    try:
        print("Auditing candidate records for missing resume_blob_name...")
        missing_blob = []
        for candidate in application_container.query_items(query=query, enable_cross_partition_query=True):
            resume_uploaded = candidate.get('resume_uploaded', True)
            resume_blob_name = candidate.get('resume_blob_name')
            if resume_uploaded and not resume_blob_name:
                missing_blob.append(candidate)
                logging.warning(f"Candidate {candidate.get('email')} for job {candidate.get('job_id')} is missing resume_blob_name.")
        print(f"Found {len(missing_blob)} candidates missing resume_blob_name:")
        for cand in missing_blob:
            print(f"Email: {cand.get('email')}, Job ID: {cand.get('job_id')}, ID: {cand.get('id')}")
        if not missing_blob:
            print("All candidate records have resume_blob_name present.")
        return missing_blob
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Error querying candidate records: {e}")
        return []

if __name__ == "__main__":
    audit_candidates_missing_resume_blob()
