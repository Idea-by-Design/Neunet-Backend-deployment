from common.database.cosmos.db_operations import containers, config

def get_jobs_applied_by_candidate(email=None, candidate_id=None):
    container = containers[config['database']['application_container_name']]
    if email:
        query = f"SELECT c.job_id FROM c WHERE c.email = '{email}'"
    elif candidate_id:
        query = f"SELECT c.job_id FROM c WHERE c.candidate_id = '{candidate_id}'"
    else:
        raise ValueError('Must provide email or candidate_id')
    items = list(container.query_items(query=query, enable_cross_partition_query=True))
    jobs = [item['job_id'] for item in items if 'job_id' in item]
    print(f"Jobs applied by candidate ({email or candidate_id}): {jobs}")
    return jobs

if __name__ == "__main__":
    # You can run this file directly for quick testing
    import sys
    email = None
    candidate_id = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if '@' in arg:
            email = arg
        else:
            candidate_id = arg
    get_jobs_applied_by_candidate(email=email, candidate_id=candidate_id)
