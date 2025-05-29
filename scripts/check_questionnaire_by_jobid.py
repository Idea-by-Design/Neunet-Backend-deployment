"""
Script to check if a questionnaire exists for a given job_id in the jobDescriptionQuestionnaire container.
Usage: python -m scripts.check_questionnaire_by_jobid <job_id>
"""
import sys
from azure.cosmos import CosmosClient

COSMOS_ENDPOINT = "https://neunet-cosmos-db.documents.azure.com:443/"
COSMOS_KEY = "hOlaV01rPLnOxzZf8LEbDUrs8osGbeG0R8xe3iuypkUHY5QIGsHq30eJtrrzNHmLTAM4p1nndfk8ACDbVoB1WQ=="
DATABASE_NAME = "CandidateInfoDB"
CONTAINER_NAME = "jobDescriptionQuestionnaire"

def check_questionnaire(job_id):
    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    db = client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)
    query = f'SELECT * FROM c WHERE c.job_id = "{job_id}"'
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    if items:
        print(f"[FOUND] Questionnaire exists for job_id {job_id}.")
        print(items[0])
    else:
        print(f"[NOT FOUND] No questionnaire found for job_id {job_id}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.check_questionnaire_by_jobid <job_id>")
        sys.exit(1)
    job_id = sys.argv[1]
    check_questionnaire(job_id)
