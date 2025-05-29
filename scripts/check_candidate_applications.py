from common.database.cosmos import db_operations

def check_candidate_applications(candidate_id_or_email):
    print(f"Checking applications for: {candidate_id_or_email}\n")
    apps_by_id = db_operations.fetch_applications_by_candidate(candidate_id_or_email) or []
    apps_by_email = db_operations.fetch_applications_by_candidate_email(candidate_id_or_email) or []
    print(f"Applications by candidate_id: {len(apps_by_id)}")
    for app in apps_by_id:
        print(f"  [BY_ID] Job: {app.get('job_id')}, Email: {app.get('email')}, candidate_id: {app.get('candidate_id')}")
    print(f"Applications by email: {len(apps_by_email)}")
    for app in apps_by_email:
        print(f"  [BY_EMAIL] Job: {app.get('job_id')}, Email: {app.get('email')}, candidate_id: {app.get('candidate_id')}")
    # Merge and deduplicate as in API
    seen = set()
    all_apps = []
    for app in apps_by_id + apps_by_email:
        key = (app.get('job_id'), app.get('email'))
        if key not in seen:
            seen.add(key)
            all_apps.append(app)
    print(f"\nTotal unique applications (after deduplication): {len(all_apps)}")
    for app in all_apps:
        print(f"  [UNIQUE] Job: {app.get('job_id')}, Email: {app.get('email')}, candidate_id: {app.get('candidate_id')}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python check_candidate_applications.py <candidate_id_or_email>")
        sys.exit(1)
    check_candidate_applications(sys.argv[1])
