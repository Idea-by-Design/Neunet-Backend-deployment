import uuid
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from azure.cosmos import CosmosClient
from common.utils.config_utils import load_config

# Load config
def main():
    config = load_config()
    COSMOS_ENDPOINT = config['database']['cosmos_db_uri']
    COSMOS_KEY = config['database']['cosmos_db_key']
    DATABASE_NAME = config['database']['cosmos_db_name']
    APPLICATION_CONTAINER = config['database']['application_container_name']

    # Initialize Cosmos DB client
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(APPLICATION_CONTAINER)

    # Query all candidate records (type='candidate')
    candidate_query = "SELECT * FROM c WHERE c.type = 'candidate'"
    candidates = list(container.query_items(
        query=candidate_query,
        enable_cross_partition_query=True
    ))

    # Build a mapping from email to candidate_id
    email_to_id = {}
    for candidate in candidates:
        email = candidate.get('email')
        candidate_id = candidate.get('candidate_id')
        if not email:
            continue
        if candidate_id:
            email_to_id[email] = candidate_id
        else:
            # Assign a new UUID if missing
            email_to_id[email] = str(uuid.uuid4())
            candidate['candidate_id'] = email_to_id[email]
            container.upsert_item(candidate)

    # Query all application records (type='application')
    # Optionally, filter by job_id if desired
    job_id = os.environ.get('BACKFILL_JOB_ID')  # Set this env var to limit to a specific job
    if job_id:
        app_query = f"SELECT * FROM c WHERE c.type = 'application' AND c.job_id = '{job_id}'"
    else:
        app_query = "SELECT * FROM c WHERE c.type = 'application'"
    applications = list(container.query_items(
        query=app_query,
        enable_cross_partition_query=True
    ))

    updated_count = 0
    for app in applications:
        email = app.get('email')
        candidate_id = app.get('candidate_id')
        updated = False
        if not candidate_id and email and email in email_to_id:
            app['candidate_id'] = email_to_id[email]
            updated = True
        if not email and candidate_id:
            # Try to find email by candidate_id
            for c_email, c_id in email_to_id.items():
                if c_id == candidate_id:
                    app['email'] = c_email
                    updated = True
                    break
        if updated:
            container.upsert_item(app)
            print(f"Updated application {app.get('id')} with candidate_id: {app.get('candidate_id')}, email: {app.get('email')}")
            updated_count += 1
        elif not candidate_id or not email:
            print(f"[WARNING] Could not backfill candidate_id/email for application: {app.get('id')} (job_id: {app.get('job_id')})")

    print(f"Backfill complete. Total applications updated: {updated_count}")

if __name__ == "__main__":
    main()
