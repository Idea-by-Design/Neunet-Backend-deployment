"""
Script to audit all candidate records in the applications container and report the distribution of 'ranking' values.
Usage:
    python audit_candidate_rankings.py
Run from the neunet_ai_services root directory.
"""
import sys
import os
# Always add the repo root (Neunet-Backend-deployment) to sys.path for flat repo imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import logging
from common.utils.config_utils import load_config
from azure.cosmos import CosmosClient
from collections import Counter

logging.basicConfig(level=logging.INFO)

# Load config and connect to Cosmos DB
config = load_config()
COSMOS_ENDPOINT = config['database']['cosmos_db_uri']
COSMOS_KEY = config['database']['cosmos_db_key']
DATABASE_NAME = config['database']['cosmos_db_name']
APPLICATION_CONTAINER = config['database']['application_container_name']

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(APPLICATION_CONTAINER)

def audit_candidate_rankings():
    query = "SELECT c.email, c.job_id, c.ranking FROM c WHERE c.type = 'candidate'"
    candidates = list(container.query_items(query=query, enable_cross_partition_query=True))
    ranking_counts = Counter()
    ranking_examples = {}
    for candidate in candidates:
        ranking = candidate.get('ranking', None)
        email = candidate.get('email', '')
        job_id = candidate.get('job_id', '')
        ranking_counts[ranking] += 1
        # Store a sample for each ranking value
        if ranking not in ranking_examples:
            ranking_examples[ranking] = f"email: {email}, job_id: {job_id}"
    print("Ranking Distribution (ranking: count):")
    for ranking, count in ranking_counts.items():
        print(f"  {ranking}: {count} (e.g., {ranking_examples[ranking]})")
    print(f"\nTotal candidates: {len(candidates)}")

if __name__ == "__main__":
    audit_candidate_rankings()
