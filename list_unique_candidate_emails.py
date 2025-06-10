from common.database.cosmos.db_operations import ensure_containers

containers = ensure_containers()
container = containers['applications']
unique_emails = set()
for item in container.query_items(query="SELECT * FROM c WHERE c.type = 'candidate'", enable_cross_partition_query=True):
    email = item.get('email')
    if email:
        unique_emails.add(email)
print(f"Total unique candidate emails: {len(unique_emails)}")
print("Emails:")
for e in sorted(unique_emails):
    print(e)
