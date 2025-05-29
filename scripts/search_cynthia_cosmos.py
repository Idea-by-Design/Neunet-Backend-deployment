from azure.cosmos import CosmosClient

COSMOS_ENDPOINT = "https://services.mos-db.documents.azure.com:443/"
COSMOS_KEY = "hOlaV01rPLnOxzZf8LEbDUrs8osGbeG0R8xe3iuypkUHY5QIGsHq30eJtrrzNHmLTAM4p1nndfk8ACDbVoB1WQ=="
DATABASE_NAME = "CandidateInfoDB"

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
results = []

for container in database.list_containers():
    container_name = container['id']
    print(f"Searching in container: {container_name}")
    container_client = database.get_container_client(container_name)
    query = """
        SELECT * FROM c
        WHERE CONTAINS(LOWER(c.email), 'cynthia')
           OR CONTAINS(LOWER(c.name), 'cynthia')
    """
    found = False
    for item in container_client.query_items(query=query, enable_cross_partition_query=True):
        print(f"Found in {container_name}: {item}")
        found = True
    if not found:
        print(f"No records found for Cynthia in {container_name}.")
    print("---")
