import yaml
from neunet_ai_services.common.database.cosmos.db_setup import setup_database
from neunet_ai_services.common.database.cosmos.db_operations import upsert_resume

# Load configuration
with open("config/config.yaml", 'r') as file:
    config = yaml.safe_load(file)

# Setup database connection
_, container = setup_database(
    config['database']['cosmos_db_uri'],
    config['database']['cosmos_db_key'],
    config['database']['cosmos_db_name'],
    config['database']['container_name']
)

# Sample data
sample_resume = {
    "id": "sample-id",
    "name": "Sample Name",
    "email": "sample@example.com"
}

# Upsert sample data
upsert_resume(container, sample_resume)
