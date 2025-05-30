from common.database.cosmos.db_operations import containers, config

if __name__ == "__main__":
    container = containers[config['database']['application_container_name']]
    try:
        container.delete_item(item='996137_cynthia@beamjobs.com', partition_key='996137')
        print("Deleted application record: 996137_cynthia@beamjobs.com (partition_key: 996137)")
    except Exception as e:
        print(f"Error deleting application: {e}")
