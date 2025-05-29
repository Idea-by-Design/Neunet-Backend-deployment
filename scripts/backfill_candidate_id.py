import uuid
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from azure.cosmos import CosmosClient
from neunet_ai_services.common.utils.config_utils import load_config

# Load config
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
query = "SELECT * FROM c WHERE c.type = 'candidate'"
candidates = list(container.query_items(
    query=query,
    enable_cross_partition_query=True
))

# Step 1: Build a mapping from email to candidate_id
email_to_id = {}
for candidate in candidates:
    email = candidate.get('email')
    if not email:
        continue
    if email not in email_to_id:
        email_to_id[email] = str(uuid.uuid4())

# Step 2: Assign candidate_id to all records and upsert to DB
updated_count = 0
for candidate in candidates:
    email = candidate.get('email')
    if not email:
        continue
    candidate_id = email_to_id[email]
    if candidate.get('candidate_id') != candidate_id:
        candidate['candidate_id'] = candidate_id
        container.upsert_item(candidate)
        updated_count += 1

print(f"Updated {updated_count} candidate records with candidate_id.")

# Step 2: Assign the same candidate_id for all records with the same email
count_updated = 0
for candidate in candidates:
    email = candidate.get('email')
    if not email:
        continue
    candidate['candidate_id'] = email_to_id[email]
    container.upsert_item(candidate)
    print(f"Set candidate_id for: {email} -> {candidate['candidate_id']}")
    count_updated += 1

print(f"Backfill complete. Total candidates updated: {count_updated}")

# Step 3: Backfill candidate_id into all application records for each candidate
print("\nBackfilling candidate_id into application records...")
app_updated_count = 0
for candidate in candidates:
    email = candidate.get('email')
    candidate_id = candidate.get('candidate_id')
    if not email or not candidate_id:
        continue
    # Query all non-candidate records with this email
    app_query = f"SELECT * FROM c WHERE c.email = '{email}' AND c.type != 'candidate'"
    applications = list(container.query_items(query=app_query, enable_cross_partition_query=True))
    for app in applications:
        if app.get('candidate_id') != candidate_id:
            app['candidate_id'] = candidate_id
            container.upsert_item(app)
            app_updated_count += 1
            print(f"Set candidate_id for application: {app.get('id')} -> {candidate_id}")
print(f"Backfill complete. Total application records updated: {app_updated_count}")

