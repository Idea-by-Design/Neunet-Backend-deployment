from common.database.cosmos.db_operations import containers, config

def cleanup_incomplete_candidates():
    container = containers[config['database']['application_container_name']]
    query = "SELECT * FROM c"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    deleted = 0
    for item in items:
        if not item.get('resume_blob_name'):
            print(f"Deleting incomplete candidate: {item.get('id')}")
            container.delete_item(item=item['id'], partition_key=item['job_id'])
            deleted += 1
    print(f"Deleted {deleted} incomplete candidate records.")

if __name__ == "__main__":
    cleanup_incomplete_candidates()
