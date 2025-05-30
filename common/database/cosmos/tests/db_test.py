from dotenv import load_dotenv
import os
from common.database.cosmos.db_setup import setup_database
from common.database.cosmos.db_operations import upsert_resume

# Load environment variables from .env at project root
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../../.env'))

# Setup database connection using environment variables
COSMOS_DB_URI = os.environ['COSMOS_DB_URI']
COSMOS_DB_KEY = os.environ['COSMOS_DB_KEY']
COSMOS_DB_NAME = os.environ['COSMOS_DB_NAME']
APPLICATION_CONTAINER_NAME = os.environ['APPLICATION_CONTAINER_NAME']

_, container = setup_database(
    COSMOS_DB_URI,
    COSMOS_DB_KEY,
    COSMOS_DB_NAME,
    APPLICATION_CONTAINER_NAME
)

# Sample data
sample_resume = {
    "id": "sample-id",
    "name": "Sample Name",
    "email": "sample@example.com"
}

# Upsert sample data
upsert_resume(sample_resume)
