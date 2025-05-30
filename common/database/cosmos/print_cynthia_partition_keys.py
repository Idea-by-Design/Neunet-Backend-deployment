from common.database.cosmos.db_operations import containers, config

if __name__ == "__main__":
    container = containers[config['database']['application_container_name']]
    query = "SELECT * FROM c WHERE c.email = 'cynthia@beamjobs.com'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    print(f"Found {len(items)} records for cynthia@beamjobs.com:")
    for item in items:
        print("---")
        print(f"id: {item.get('id')}")
        print(f"job_id: {item.get('job_id')}")
        # Print all possible partition keys
        print(f"Partition key candidates:")
        for key in ['job_id', 'email', 'candidate_id', 'id']:
            print(f"  {key}: {item.get(key)}")
        print(f"Full record: {item}")
