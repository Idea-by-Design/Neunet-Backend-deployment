"""
Script to backfill and fix candidate_id in job application records.
Ensures all applications for a given email have the correct UUID as candidate_id.
"""

from azure.cosmos import CosmosClient
from common.utils.config_utils import load_config
import uuid

config = load_config()
COSMOS_ENDPOINT = config['database']['cosmos_db_uri']
COSMOS_KEY = config['database']['cosmos_db_key']
DATABASE_NAME = config['database']['cosmos_db_name']
APPLICATION_CONTAINER = config['database']['application_container_name']

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(APPLICATION_CONTAINER)

def backfill_candidate_ids():
    print('Scanning all applications...')
    email_to_uuid = {}
    updated = 0
    # Query all applications
    query = "SELECT * FROM c"
    for item in container.query_items(query=query, enable_cross_partition_query=True):
        email = item.get('email')
        candidate_id = item.get('candidate_id')
        # If candidate_id is missing or looks like an email, fix it
        if not candidate_id or (isinstance(candidate_id, str) and '@' in candidate_id):
            if email in email_to_uuid:
                new_cid = email_to_uuid[email]
            else:
                # Try to find an existing UUID for this email
                existing = [i for i in container.query_items(
                    query=f"SELECT * FROM c WHERE c.email = '{email}' AND IS_DEFINED(c.candidate_id)",
                    enable_cross_partition_query=True
                ) if i.get('candidate_id') and '@' not in i.get('candidate_id')]
                if existing:
                    new_cid = existing[0]['candidate_id']
                else:
                    new_cid = str(uuid.uuid4())
                email_to_uuid[email] = new_cid
            print(f"Fixing candidate_id for {email}: {candidate_id} -> {new_cid}")
            item['candidate_id'] = new_cid
            container.replace_item(item=item['id'], body=item)
            updated += 1
    print(f"Backfill complete. Updated {updated} application records.")

if __name__ == "__main__":
    backfill_candidate_ids()
