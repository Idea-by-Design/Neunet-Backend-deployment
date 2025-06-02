"""
Copy parsed_resume from one job application to another for the same candidate.
"""
from azure.cosmos import CosmosClient
from common.utils.config_utils import load_config

config = load_config()
COSMOS_ENDPOINT = config['database']['cosmos_db_uri']
COSMOS_KEY = config['database']['cosmos_db_key']
DATABASE_NAME = config['database']['cosmos_db_name']
APPLICATION_CONTAINER = config['database']['application_container_name']

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(APPLICATION_CONTAINER)

# Inputs
target_job_id = '327810'
target_email = 'cynthia@beamjobs.com'
target_candidate_id = 'e6a2446c-e921-467e-9e5a-eb7c7a661ece'
source_job_id = '603411'

# Fetch source application (with parsed_resume)
source_query = f"SELECT * FROM c WHERE c.job_id = '{source_job_id}' AND c.candidate_id = '{target_candidate_id}'"
source_apps = list(container.query_items(query=source_query, enable_cross_partition_query=True))
if not source_apps or not source_apps[0].get('parsed_resume'):
    print('Source application with parsed_resume not found!')
    exit(1)
parsed_resume = source_apps[0]['parsed_resume']

# Fetch target application
query = f"SELECT * FROM c WHERE c.job_id = '{target_job_id}' AND c.candidate_id = '{target_candidate_id}' AND c.email = '{target_email}'"
target_apps = list(container.query_items(query=query, enable_cross_partition_query=True))
if not target_apps:
    print('Target application not found!')
    exit(1)
target_app = target_apps[0]
target_app['parsed_resume'] = parsed_resume
container.replace_item(item=target_app['id'], body=target_app)
print(f"Successfully copied parsed_resume from job {source_job_id} to job {target_job_id} for candidate {target_candidate_id}")
