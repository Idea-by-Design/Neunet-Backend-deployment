from common.database.cosmos.db_operations import containers, config

def remove_job_from_candidate(email, job_id):
    container = containers[config['database']['application_container_name']]
    # Remove all application records for this candidate and job_id
    query = f"SELECT * FROM c WHERE c.email = '{email}' AND c.job_id = '{job_id}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    deleted = 0
    for item in items:
        print(f"Deleting application: {item.get('id')}")
        container.delete_item(item=item['id'], partition_key=item['job_id'])
        deleted += 1
    print(f"Deleted {deleted} application(s) for candidate {email} and job_id {job_id}")
    # Also remove job_id from any jobs_applied, applied_jobs, job_ids fields in other records for this candidate
    query = f"SELECT * FROM c WHERE c.email = '{email}'"
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    cleaned = 0
    for item in items:
        changed = False
        for field in ['jobs_applied', 'applied_jobs', 'job_ids']:
            if field in item and isinstance(item[field], list):
                before = set(item[field])
                item[field] = [jid for jid in item[field] if str(jid) != str(job_id)]
                after = set(item[field])
                if before != after:
                    print(f"Cleaned {field} for {item.get('id')}")
                    changed = True
        if changed:
            container.upsert_item(item)
            cleaned += 1
    print(f"Cleaned {cleaned} candidate records for {email}")

if __name__ == "__main__":
    remove_job_from_candidate('cynthia@beamjobs.com', '996137')
