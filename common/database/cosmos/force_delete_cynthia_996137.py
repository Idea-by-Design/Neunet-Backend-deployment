from common.database.cosmos.db_operations import containers, config

if __name__ == "__main__":
    container = containers[config['database']['application_container_name']]
    # Try all possible partition keys for deletion
    possible_keys = ['996137', 'cynthia@beamjobs.com', '996137_cynthia@beamjobs.com']
    for pk in possible_keys:
        try:
            container.delete_item(item='996137_cynthia@beamjobs.com', partition_key=pk)
            print(f"Deleted with partition_key: {pk}")
        except Exception as e:
            print(f"Attempt with partition_key {pk} failed: {e}")
