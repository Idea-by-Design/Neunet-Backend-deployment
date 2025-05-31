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

    # Build a mapping from candidate_id to email
    id_to_email = {}
    for candidate in candidates:
        email = candidate.get('email')
        candidate_id = candidate.get('candidate_id')
        if email and candidate_id:
            id_to_email[candidate_id] = email

    # Query all application records (type='application')
    app_query = "SELECT * FROM c WHERE c.type = 'application'"
    applications = list(container.query_items(
        query=app_query,
        enable_cross_partition_query=True
    ))

    updated_count = 0
    for app in applications:
        email = app.get('email')
        candidate_id = app.get('candidate_id')
        if not email and candidate_id and candidate_id in id_to_email:
            app['email'] = id_to_email[candidate_id]
            container.upsert_item(app)
            print(f"Set email for application {app.get('id')}: {app['email']}")
            updated_count += 1
        elif not email:
            print(f"[WARNING] Could not backfill email for application: {app.get('id')} (candidate_id: {candidate_id})")
    print(f"Backfill complete. Total applications updated: {updated_count}")

if __name__ == "__main__":
    main()
