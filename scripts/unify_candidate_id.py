from common.database.cosmos import db_operations

def unify_candidate_id_for_email(email, canonical_candidate_id=None):
    apps = db_operations.fetch_applications_by_candidate_email(email) or []
    if not apps:
        print(f"No applications found for email: {email}")
        return
    if canonical_candidate_id is None:
        # Use the candidate_id from the first application as the canonical one
        canonical_candidate_id = apps[0].get('candidate_id')
        if not canonical_candidate_id:
            import uuid
            canonical_candidate_id = str(uuid.uuid4())
    print(f"Canonical candidate_id to use: {canonical_candidate_id}")
    updated = 0
    for app in apps:
        if app.get('candidate_id') != canonical_candidate_id:
            print(f"Updating job {app.get('job_id')} from candidate_id {app.get('candidate_id')} to {canonical_candidate_id}")
            app['candidate_id'] = canonical_candidate_id
            db_operations.upsert_candidate(app)
            updated += 1
    print(f"Updated {updated} applications to use candidate_id {canonical_candidate_id}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python unify_candidate_id.py <email> [<canonical_candidate_id>]")
        sys.exit(1)
    email = sys.argv[1]
    canonical_candidate_id = sys.argv[2] if len(sys.argv) > 2 else None
    unify_candidate_id_for_email(email, canonical_candidate_id)
