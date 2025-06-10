from common.database.cosmos.db_operations import ensure_containers

containers = ensure_containers()
container = containers['applications']
email_to_check = 'akhyasingh20@gmail.com'
for item in container.query_items(query="SELECT * FROM c WHERE c.type = 'candidate'", enable_cross_partition_query=True):
    email = item.get('email')
    if email == email_to_check:
        print(f"Candidate for {email}: candidate_id={item.get('candidate_id')}, id={item.get('id')}, status={item.get('status')}, resume={item.get('resume')}")
