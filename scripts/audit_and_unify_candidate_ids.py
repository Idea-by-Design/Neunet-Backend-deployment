from collections import defaultdict, Counter
from common.database.cosmos import db_operations

def fetch_all_candidate_applications():
    # Directly query the Cosmos container for all candidate/application docs
    containers = db_operations.containers
    config = db_operations.config
    container = containers[config['database']['application_container_name']]
    # Query for all docs with type 'candidate' or 'application'
    query = "SELECT * FROM c WHERE c.type = 'candidate' OR c.type = 'application'"
    return list(container.query_items(query=query, enable_cross_partition_query=True))

def audit_and_unify_all_candidates(dry_run=True):
    all_apps = fetch_all_candidate_applications()
    if not all_apps:
        print("No applications found in DB.")
        return
    email_to_candidate_ids = defaultdict(list)
    email_to_apps = defaultdict(list)
    for app in all_apps:
        email = app.get('email')
        cid = app.get('candidate_id')
        if email and cid:
            email_to_candidate_ids[email].append(cid)
            email_to_apps[email].append(app)
    inconsistent = {email: Counter(cids) for email, cids in email_to_candidate_ids.items() if len(set(cids)) > 1}
    print(f"Found {len(inconsistent)} emails with inconsistent candidate_ids.")
    for email, cid_counts in inconsistent.items():
        print(f"Email: {email}")
        print(f"  Candidate IDs: {dict(cid_counts)}")
        canonical_cid = cid_counts.most_common(1)[0][0]
        print(f"  Canonical candidate_id: {canonical_cid}")
        if not dry_run:
            for app in email_to_apps[email]:
                if app.get('candidate_id') != canonical_cid:
                    print(f"    Updating job {app.get('job_id')} from {app.get('candidate_id')} to {canonical_cid}")
                    app['candidate_id'] = canonical_cid
                    db_operations.upsert_candidate(app)
    if dry_run:
        print("\n(DRY RUN) No records were updated. Run with --apply to apply changes.")
    else:
        print("All inconsistent candidate_ids have been unified.")

if __name__ == "__main__":
    import sys
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--apply':
        dry_run = False
    audit_and_unify_all_candidates(dry_run=dry_run)
