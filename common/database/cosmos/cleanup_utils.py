from common.database.cosmos.db_operations import containers, config

def cleanup_invalid_job_references(invalid_job_ids=None):
    """
    Remove references to invalid/deleted job IDs from all candidate/application records.
    """
    if invalid_job_ids is None:
        invalid_job_ids = ['996137']
    container = containers[config['database']['application_container_name']]
    query = "SELECT * FROM c"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    cleaned = 0
    for item in items:
        changed = False
        # Remove job_id if it's invalid
        if 'job_id' in item and str(item['job_id']) in invalid_job_ids:
            print(f"Removing entire record for invalid job_id {item['job_id']} (id={item.get('id')})")
            container.delete_item(item=item['id'], partition_key=item['job_id'])
            cleaned += 1
            continue
        # Remove from jobs_applied or similar fields
        for field in ['jobs_applied', 'applied_jobs', 'job_ids']:
            if field in item and isinstance(item[field], list):
                before = set(item[field])
                item[field] = [jid for jid in item[field] if str(jid) not in invalid_job_ids]
                after = set(item[field])
                if before != after:
                    print(f"Cleaned {field} for {item.get('email') or item.get('id')}")
                    changed = True
        if changed:
            container.upsert_item(item)
            cleaned += 1
    print(f"Cleanup complete. Cleaned {cleaned} records.")
    return cleaned
