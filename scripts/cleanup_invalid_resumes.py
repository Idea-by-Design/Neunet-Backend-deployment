import os
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
COSMOS_ENDPOINT = os.getenv('COSMOS_DB_URI')
COSMOS_KEY = os.getenv('COSMOS_DB_KEY')
DATABASE_NAME = os.getenv('COSMOS_DB_NAME')
CONTAINER_NAME = os.getenv('APPLICATION_CONTAINER_NAME')

print(f"COSMOS_DB_URI: {COSMOS_ENDPOINT} ({type(COSMOS_ENDPOINT)})")
print(f"COSMOS_DB_KEY: {str(COSMOS_KEY)[:5]}... (masked) ({type(COSMOS_KEY)})")
print(f"COSMOS_DB_NAME: {DATABASE_NAME} ({type(DATABASE_NAME)})")
print(f"APPLICATION_CONTAINER_NAME: {CONTAINER_NAME} ({type(CONTAINER_NAME)})")

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

def find_and_clean_invalid_resumes():
    print('Scanning for candidate records with missing or empty resume_blob_name...')
    query = "SELECT * FROM c WHERE c.type = 'candidate'"
    candidates = list(container.query_items(query=query, enable_cross_partition_query=True))
    count = 0
    for candidate in candidates:
        if not candidate.get('resume_blob_name'):
            print(f"Cleaning candidate {candidate.get('email')} for job {candidate.get('job_id')}")
            candidate['resume_blob_name'] = None
            container.upsert_item(candidate)
            count += 1
    print(f"Cleanup complete. {count} records updated.")

if __name__ == '__main__':
    find_and_clean_invalid_resumes()
