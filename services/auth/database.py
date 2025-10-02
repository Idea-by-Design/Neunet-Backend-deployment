import os
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from dotenv import load_dotenv

load_dotenv()

# Cosmos DB configuration
COSMOS_URI = os.getenv("COSMOS_DB_URI")
COSMOS_KEY = os.getenv("COSMOS_DB_KEY")
DATABASE_NAME = os.getenv("COSMOS_DB_NAME", "CandidateInfoDB")
USERS_CONTAINER_NAME = "users"

# Initialize Cosmos client
client = CosmosClient(COSMOS_URI, COSMOS_KEY)

# Get or create database
try:
    database = client.create_database_if_not_exists(id=DATABASE_NAME)
    print(f"Database '{DATABASE_NAME}' ready")
except exceptions.CosmosResourceExistsError:
    database = client.get_database_client(DATABASE_NAME)
    print(f"Database '{DATABASE_NAME}' already exists")

# Get or create users container (without dedicated throughput to use shared database throughput)
try:
    users_container = database.create_container_if_not_exists(
        id=USERS_CONTAINER_NAME,
        partition_key=PartitionKey(path="/email")
        # No offer_throughput specified - will use shared database throughput
    )
    print(f"Container '{USERS_CONTAINER_NAME}' ready")
except exceptions.CosmosResourceExistsError:
    users_container = database.get_container_client(USERS_CONTAINER_NAME)
    print(f"Container '{USERS_CONTAINER_NAME}' already exists")
except exceptions.CosmosHttpResponseError as e:
    # If container creation fails, try to get existing container
    print(f"Note: {e.message}")
    try:
        users_container = database.get_container_client(USERS_CONTAINER_NAME)
        print(f"Using existing container '{USERS_CONTAINER_NAME}'")
    except:
        raise Exception(f"Failed to create or access container: {e}")

def get_users_container():
    """Get the users container"""
    return users_container
