from azure.cosmos import CosmosClient, PartitionKey, exceptions
from common.utils.config_utils import load_config
from datetime import datetime
import ast
import uuid


# Load configuration
config = load_config()
COSMOS_ENDPOINT = config['database']['cosmos_db_uri']
COSMOS_KEY = config['database']['cosmos_db_key']
DATABASE_NAME = config['database']['cosmos_db_name']

# Initialize Cosmos DB client
print(f"Connecting to Cosmos DB at {COSMOS_ENDPOINT}")
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)

# Ensure database exists
try:
    print(f"Creating database if not exists: {DATABASE_NAME}")
    database = client.create_database_if_not_exists(id=DATABASE_NAME, offer_throughput=1000)
    print(f"Using database: {DATABASE_NAME}")
except Exception as e:
    print(f"Error creating/accessing database: {e}")
    raise e

def update_candidate_status_by_id(job_id, candidate_id, status):
    valid_statuses = [
        "Applied",
        "Application Under Review",
        "Interview Invite Sent",
        "Interview Scheduled",
        "Interview Feedback Under Review",
        "Offer Extended",
        "Rejected",
        "Withdrawn",
        "Shortlisted"
    ]
    try:
        print(f"[DEBUG] update_candidate_status_by_id called with job_id={job_id}, candidate_id={candidate_id}, status={status}")
        query = f"SELECT * FROM c WHERE c.candidate_id = '{candidate_id}' AND c.job_id = '{job_id}'"
        candidates = list(containers[config['database']['application_container_name']].query_items(query=query, enable_cross_partition_query=True))
        if not candidates:
            print(f"[DEBUG] No candidate found with candidate_id={candidate_id} and job_id={job_id}")
            return f"Error: Candidate with candidate_id {candidate_id} not found for job ID {job_id}."
        candidate = candidates[0]
        print(f"[DEBUG] Found candidate: {candidate.get('email')} (candidate_id={candidate_id})")
        # Case-insensitive status validation
        status_map = {s.lower(): s for s in valid_statuses}
        normalized_status = status_map.get(status.lower())
        if normalized_status:
            candidate["application_status"] = normalized_status
            candidate["status"] = normalized_status
            print(f"[DEBUG] Setting status to {normalized_status}")
        else:
            candidate["application_status"] = "Unknown"
            candidate["status"] = "Unknown"
            print(f"[DEBUG] Invalid status, setting to Unknown")
        containers[config['database']['application_container_name']].replace_item(item=candidate["id"], body=candidate)
        print(f"[DEBUG] Status for {candidate_id} updated to '{status}'")
        return f"Success: Status for {candidate_id} updated to '{status}'."
    except Exception as e:
        print(f"[DEBUG] An error occurred: {e}")
        return f"An error occurred: {e}"

# Fetch applications by candidate_id (for UUID lookup)
def fetch_applications_by_candidate(candidate_id):
    global containers, config
    query = f"SELECT * FROM c WHERE c.candidate_id = '{candidate_id}'"
    return list(containers[config['database']['application_container_name']].query_items(query=query, enable_cross_partition_query=True))

# Fetch applications by candidate email (for fallback lookup)
def fetch_applications_by_candidate_email(email):
    global containers, config
    query = f"SELECT * FROM c WHERE c.email = '{email}'"
    return list(containers[config['database']['application_container_name']].query_items(query=query, enable_cross_partition_query=True))

# Initialize containers
def ensure_containers():
    containers = {}
    try:
        print("Creating containers if they don't exist")
        containers[config['database']['resumes_container_name']] = database.create_container_if_not_exists(
            id=config['database']['resumes_container_name'],
            partition_key=PartitionKey(path="/email")
        )
        containers[config['database']['github_container_name']] = database.create_container_if_not_exists(
            id=config['database']['github_container_name'],
            partition_key=PartitionKey(path="/email")
        )
        containers[config['database']['ranking_container_name']] = database.create_container_if_not_exists(
            id=config['database']['ranking_container_name'],
            partition_key=PartitionKey(path="/job_id")
        )
        containers[config['database']['job_description_container_name']] = database.create_container_if_not_exists(
            id=config['database']['job_description_container_name'],
            partition_key=PartitionKey(path="/job_id")
        )
        containers[config['database']['application_container_name']] = database.create_container_if_not_exists(
            id=config['database']['application_container_name'],
            partition_key=PartitionKey(path="/job_id")
        )
        containers[config['database']['job_description_questionnaire_container_name']] = database.create_container_if_not_exists(
            id=config['database']['job_description_questionnaire_container_name'],
            partition_key=PartitionKey(path="/job_id")
        )
        print("All containers ready")
        return containers
    except Exception as e:
        print(f"Error creating containers: {e}")
        raise e

# Initialize containers
print("Initializing containers...")
containers = ensure_containers()

def upsert_resume(resume_data):
    try:
        print(f"Upserting resume for {resume_data['email']}")
        containers[config['database']['resumes_container_name']].upsert_item(resume_data)
        print(f"Resume data upserted successfully!")
    except Exception as e:
        print(f"An error occurred while upserting resume: {e}")

def upsert_jobDetails(jobData):
    try:
        print("Upserting job data:", jobData)
        # Ensure both id and job_id are present
        if "id" not in jobData and "job_id" in jobData:
            jobData["id"] = jobData["job_id"]
        elif "job_id" not in jobData and "id" in jobData:
            jobData["job_id"] = jobData["id"]
            
        print("Final job data to upsert:", jobData)
        containers[config['database']['job_description_container_name']].upsert_item(jobData)
        print(f"Job data upserted successfully!")
        
        # Verify the job was saved
        saved_job = fetch_job_description(jobData["job_id"])
        print("Verified saved job:", saved_job)
        
    except Exception as e:
        print(f"An error occurred while upserting job: {e}")
        print("Saving candidate data:", application_data)
        fetch_resume_with_email_and_job(job_id, email)
        upsert_candidate(application_data)

def delete_job(job_id):
    """
    Delete a job from the job description container by job_id.
    """
    try:
        container = containers[config['database']['job_description_container_name']]
        container.delete_item(item=job_id, partition_key=job_id)
        print(f"Job {job_id} deleted successfully.")
        return True
    except Exception as e:
        print(f"Failed to delete job {job_id}: {e}")
        return False

def delete_applications_by_job_id(job_id):
    """
    Delete all candidate application records for a given job_id from the application container.
    """
    try:
        container = containers[config['database']['application_container_name']]
        query = f"SELECT c.id FROM c WHERE c.job_id = '{job_id}'"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        for item in items:
            container.delete_item(item=item['id'], partition_key=job_id)
            print(f"Deleted application {item['id']} for job {job_id}")
        print(f"All applications for job {job_id} deleted.")
        return True
    except Exception as e:
        print(f"Failed to delete applications for job {job_id}: {e}")
        return False

        print("Upserting job data:", jobData)
        # Ensure both id and job_id are present
        if "id" not in jobData and "job_id" in jobData:
            jobData["id"] = jobData["job_id"]
        elif "job_id" not in jobData and "id" in jobData:
            jobData["job_id"] = jobData["id"]
            
        print("Final job data to upsert:", jobData)
        containers[config['database']['job_description_container_name']].upsert_item(jobData)
        print(f"Job data upserted successfully!")
        
        # Verify the job was saved
        saved_job = fetch_job_description(jobData["job_id"])
        print("Verified saved job:", saved_job)
        
    except Exception as e:
        print(f"An error occurred while upserting job: {e}")
        print("Saving candidate data:", application_data)
        fetch_resume_with_email_and_job(job_id, email)
        upsert_candidate(application_data)

def upsert_candidate(candidate_data):
    """
    Upsert a candidate application into the database.
    Adds a globally unique candidate_id if not present.
    Ensures 'resume_blob_name' is present if a resume is uploaded.
    Ensures candidate_id is consistent for all applications with the same email.
    """
    try:
        print(f"Upserting candidate application for job {candidate_data['job_id']}")
        print("Candidate data to upsert:", candidate_data)
        # Validate presence of resume_blob_name if a resume is uploaded
        if candidate_data.get('resume_uploaded', True):  # Assume True if not specified
            if not candidate_data.get('resume_blob_name'):
                print(f"WARNING: Candidate {candidate_data.get('email')} for job {candidate_data.get('job_id')} is missing 'resume_blob_name'.")
                raise ValueError(f"Missing 'resume_blob_name' for candidate {candidate_data.get('email')} and job {candidate_data.get('job_id')}")
        # Ensure candidate_id is consistent for email
        if not candidate_data.get("candidate_id"):
            # Look for existing applications for this email
            existing_apps = fetch_applications_by_candidate_email(candidate_data["email"])
            existing_cids = [app.get("candidate_id") for app in existing_apps if app.get("candidate_id")]
            if existing_cids:
                candidate_data["candidate_id"] = existing_cids[0]
                print(f"Reusing candidate_id {candidate_data['candidate_id']} for email {candidate_data['email']}")
            else:
                candidate_data["candidate_id"] = str(uuid.uuid4())
                print(f"Generated new candidate_id: {candidate_data['candidate_id']}")
        # Create composite ID from job_id and email
        candidate_data["id"] = f"{candidate_data['job_id']}_{candidate_data['email']}"
        containers[config['database']['application_container_name']].upsert_item(candidate_data)
        print(f"Candidate application upserted successfully!")
        return candidate_data
    except Exception as e:
        print(f"An error occurred while upserting candidate: {e}")
        raise e

def fetch_job_description(job_id):
    try:
        query = f"SELECT * FROM c WHERE c.job_id = '{job_id}'"
        items = list(containers[config['database']['job_description_container_name']].query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
    except Exception as e:
        print(f"An error occurred while fetching job description: {e}")
        return None

def fetch_top_k_candidates_by_count(job_id, top_k=10):
    try:
        query = f"""
        SELECT *
        FROM c
        WHERE c.job_id = '{job_id}'
        """
        candidates = list(containers[config['database']['application_container_name']].query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        print("RAW CANDIDATES:", candidates)  # Debug print
        # Filter out incomplete candidates (missing resume_blob_name)
        valid_candidates = [c for c in candidates if c.get('resume_blob_name')]
        print("VALID CANDIDATES:", valid_candidates)  # Debug print
        print(f"Found {len(valid_candidates)} valid candidates for job {job_id}")

        # Fetch rankings for this job
        rankings = fetch_candidate_rankings(job_id)
        # Attach ranking and ensure job_id/candidate_id for each candidate
        for c in valid_candidates:
            email = c.get('email') or c.get('candidate_email')
            ranking_info = rankings.get(email, {})
            c['ranking'] = ranking_info.get('ranking', c.get('ranking', None))
            c['job_id'] = c.get('job_id', job_id)
            if not c.get('candidate_id'):
                # Try to extract from id if possible
                if c.get('id') and '_' in c['id']:
                    c['candidate_id'] = c['id'].split('_', 1)[-1]
        # Sort by ranking descending, fallback to original order if no ranking
        sorted_candidates = sorted(valid_candidates, key=lambda x: x.get('ranking', 0), reverse=True)
        # Limit to top_k
        top_candidates = sorted_candidates[:top_k]
        print(f"Returning top {top_k} candidates for job {job_id}")
        import json
        return json.dumps(top_candidates)
    except Exception as e:
        print(f"An error occurred while fetching candidates: {e}")
        return []

def get_candidate_id_by_email(job_id, email):
    """
    Given a job_id and candidate email, return the candidate_id (UUID) if found, else None.
    """
    try:
        query = f"SELECT * FROM c WHERE c.job_id = '{job_id}' AND c.email = '{email}'"
        candidates = list(containers[config['database']['application_container_name']].query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        if candidates:
            candidate = candidates[0]
            # Prefer the candidate_id field, else extract from id
            if candidate.get('candidate_id'):
                return candidate['candidate_id']
            elif candidate.get('id') and '_' in candidate['id']:
                parts = candidate['id'].split('_')
                # Use last part if it looks like a UUID
                if len(parts) > 1 and len(parts[-1]) > 20:
                    return parts[-1]
        return None
    except Exception as e:
        print(f"Error in get_candidate_id_by_email: {e}")
        return None

def fetch_top_k_candidates_by_percentage(job_id, top_percent=0.1):
    """
    Fetch the top X% of candidates for a given job_id.
    :param job_id: str, the job to query for
    :param top_percent: float, e.g. 0.1 for top 10%
    :return: list of candidate dicts
    """
    try:
        # Fetch all valid candidates for the job
        candidates = fetch_top_k_candidates_by_count(job_id, top_k=10000)
        if not candidates:
            return []
        # Calculate how many candidates to return
        count = max(1, int(len(candidates) * top_percent))
        # Optionally, sort candidates by a ranking score if available
        sorted_candidates = sorted(
            candidates,
            key=lambda c: c.get('ranking', 0),
            reverse=True
        )
        return sorted_candidates[:count]
    except Exception as e:
        print(f"An error occurred in fetch_top_k_candidates_by_percentage: {e}")
        return []

def update_application_status(job_id, candidate_id, new_status):
    """
    Update the application status for a candidate in a given job.
    """
    try:
        container = containers[config['database']['application_container_name']]
        query = f"SELECT * FROM c WHERE c.job_id = '{job_id}' AND c.candidate_id = '{candidate_id}'"
        items = list(container.query_items(query=query, enable_cross_partition_query=True))
        if not items:
            print(f"No application found for job_id={job_id} and candidate_id={candidate_id}")
            return False
        application = items[0]
        application['application_status'] = new_status
        application['status'] = new_status  # in case both are used
        container.replace_item(item=application['id'], body=application)
        print(f"Updated application status for job_id={job_id}, candidate_id={candidate_id} to '{new_status}'")
        return True
    except Exception as e:
        print(f"Error updating application status: {e}")
        return False

def fetch_all_jobs():
    try:
        query = "SELECT * FROM c ORDER BY c._ts DESC"
        jobs = list(containers[config['database']['job_description_container_name']].query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return jobs
    except Exception as e:
        print(f"An error occurred while fetching all jobs: {e}")
        return []

def fetch_candidates_with_github_links():
    import json
    try:
        query = """
        SELECT c.email, c.resume
        FROM c
        WHERE c.type = 'candidate' AND IS_DEFINED(c.resume)
        """
        print("Executing query to fetch candidates with resumes...")
        candidates = list(containers[config['database']['application_container_name']].query_items(query=query, enable_cross_partition_query=True))
        print(f"Fetched {len(candidates)} candidate documents.")
        results = []
        for candidate in candidates:
            email = candidate.get('email')
            resume_json = candidate.get('resume')
            if not resume_json:
                continue
            try:
                resume = json.loads(resume_json)
            except Exception as e:
                print(f"[WARN] Could not parse resume JSON for {email}: {e}")
                continue
            github_link = resume.get('links', {}).get('gitHub')
            if github_link:
                results.append({'email': email, 'github': github_link})
                print(f"[INFO] Found GitHub link for {email}: {github_link}")
        print(f"Returning {len(results)} candidates with GitHub links.")
        return results
    except Exception as e:
        print(f"An error occurred while fetching candidates: {e}")
        return []

# --- Candidate-based GitHub Analysis Storage ---
def upsert_github_analysis(candidate_email, github_identifier, analysis_result):
    """Upsert GitHub analysis for a candidate (by email + github_identifier)"""
    print(f"[DEBUG] Attempting upsert_github_analysis with candidate_email={candidate_email}, github_identifier={github_identifier}")
    print(f"[DEBUG] Analysis result: {repr(analysis_result)[:300]}")
    item = {
        "id": f"github_analysis_{candidate_email}_{github_identifier}",
        "candidate_email": candidate_email,
        "github_identifier": github_identifier,
        "type": "github_analysis",
        "result": analysis_result,
        "created_at": datetime.utcnow().isoformat(),
        "email": candidate_email  # for partition key compatibility
    }
    try:
        containers[config['database']['github_container_name']].upsert_item(item)
        print(f"[INFO] GitHub analysis upserted for candidate_email={candidate_email}, github_identifier={github_identifier}")
    except Exception as e:
        print(f"[ERROR] Upsert failed: {e}")
        # If conflict, fetch existing, update, and replace
        if hasattr(e, 'status_code') and e.status_code == 409:
            print(f"[DEBUG] Conflict detected. Attempting to update existing record for candidate_email={candidate_email}, github_identifier={github_identifier}")
            query = (
                f"SELECT * FROM c WHERE c.type = 'github_analysis' "
                f"AND c.candidate_email = '{candidate_email}' "
                f"AND c.github_identifier = '{github_identifier}'"
            )
            print(f"[DEBUG] Running fallback query: {query}")
            existing = list(containers[config['database']['github_container_name']].query_items(query=query, enable_cross_partition_query=True))
            print(f"[DEBUG] Fallback query returned {len(existing)} results: {existing}")
            if existing:
                doc = existing[0]
                print(f"[DEBUG] Existing doc id: {doc.get('id')}, partition_key: {doc.get('email')}")
                doc['result'] = analysis_result
                doc['created_at'] = datetime.utcnow().isoformat()
                containers[config['database']['github_container_name']].replace_item(item=doc['id'], partition_key=doc['email'], body=doc)
                print(f"[INFO] Existing GitHub analysis updated for candidate_email={candidate_email}, github_identifier={github_identifier}")
            else:
                print(f"[ERROR] Conflict but no existing record found for candidate_email={candidate_email}, github_identifier={github_identifier}")
        else:
            raise

def fetch_github_analysis_by_candidate(candidate_email, github_identifier, return_full_item=False):
    """
    Fetch GitHub analysis for a candidate (by email + github_identifier).
    If return_full_item is True, return the full record (including created_at), else just the result.
    """
    query = (
        f"SELECT * FROM c WHERE c.type = 'github_analysis' "
        f"AND c.candidate_email = '{candidate_email}' "
        f"AND c.github_identifier = '{github_identifier}'"
    )
    results = list(containers[config['database']['github_container_name']].query_items(query=query, enable_cross_partition_query=True))
    if results:
        return results[0] if return_full_item else results[0]["result"]
    return None

# --- Async GitHub Analysis Result Storage (for polling) ---
def store_github_analysis_result(job_id, result):
    """Store async GitHub analysis result by job_id (for background task retrieval/polling)"""
    item = {
        "id": job_id,
        "job_id": job_id,
        "type": "github_analysis_result",
        "result": result,
        "created_at": datetime.utcnow().isoformat()
    }
    containers[config['database']['github_container_name']].upsert_item(item)
    print(f"[INFO] GitHub analysis result stored for job_id={job_id}")

def get_github_analysis_result(job_id):
    """Fetch async GitHub analysis result by job_id (for polling)"""
    query = f"SELECT * FROM c WHERE c.type = 'github_analysis_result' AND c.job_id = '{job_id}'"
    results = list(containers[config['database']['github_container_name']].query_items(query=query, enable_cross_partition_query=True))
    if results:
        return results[0]["result"]
    return None

# --- Async Evaluation Score Result Storage ---
def store_evaluation_score_result(job_id, candidate_email, result):
    """Store async evaluation score result for a candidate/job pair"""
    item = {
        "id": f"{job_id}_{candidate_email}_evaluation_score_result",
        "job_id": job_id,
        "candidate_email": candidate_email,
        "type": "evaluation_score_result",
        "result": result,
        "created_at": datetime.utcnow().isoformat()
    }
    containers[config['database']['github_container_name']].upsert_item(item)
    print(f"[INFO] Evaluation score result stored for job_id={job_id}, candidate_email={candidate_email}")

def get_evaluation_score_result(job_id, candidate_email):
    """Fetch async evaluation score result for a candidate/job pair"""
    query = f"SELECT * FROM c WHERE c.type = 'evaluation_score_result' AND c.job_id = '{job_id}' AND c.candidate_email = '{candidate_email}'"
    results = list(containers[config['database']['github_container_name']].query_items(query=query, enable_cross_partition_query=True))
    if results:
        return results[0]["result"]
    return None


def fetch_github_analysis(email):
    try:
        query = f"SELECT * FROM c WHERE c.type = 'github_analysis' AND c.email = '{email}'"
        results = list(containers[config['database']['github_container_name']].query_items(query=query, enable_cross_partition_query=True))
        return results[0] if results else None
    except Exception as e:
        print(f"An error occurred while fetching GitHub analysis: {e}")
        return None

def store_candidate_ranking(job_id, candidate_email, ranking, explanation=None):
    try:
        ranking_data = {
            "id": f"{job_id}_{candidate_email}",
            "job_id": job_id,
            "candidate_email": candidate_email,
            "ranking": ranking,
            "ranked_at": datetime.utcnow().isoformat(),
            "type": "ranking"
        }
        if not explanation or not isinstance(explanation, str) or not explanation.strip():
            print(f"[WARNING] store_candidate_ranking called with missing or empty explanation for job_id={job_id}, candidate_email={candidate_email}")
        else:
            ranking_data["explanation"] = explanation
        containers[config['database']['ranking_container_name']].upsert_item(ranking_data)
        print(f"Ranking stored successfully for job {job_id} and candidate {candidate_email}")
    except exceptions.CosmosHttpResponseError as e:
        print(f"Failed to store ranking: {e}")

def fetch_candidate_rankings(job_id):
    try:
        # Include explanation in the query and returned data
        query = f"SELECT c.candidate_email, c.ranking, c.ranked_at, c.explanation FROM c WHERE c.type = 'ranking' AND c.job_id = '{job_id}'"
        rankings = list(containers[config['database']['ranking_container_name']].query_items(query=query, enable_cross_partition_query=True))
        return {r['candidate_email']: {
            'ranking': r['ranking'],
            'ranked_at': r['ranked_at'],
            'explanation': r.get('explanation', None)
        } for r in rankings}
    except Exception as e:
        print(f"An error occurred while fetching candidate rankings: {e}")
        return {}

def update_recruitment_process(job_id, candidate_email, status, additional_info=None):
    valid_statuses = [
        "Applied",
        "Application Under Review",
        "Interview Invite Sent",
        "Interview Scheduled",
        "Interview Feedback Under Review",
        "Offer Extended",
        "Rejected",
        "Withdrawn",
        "Shortlisted"
    ]

    try:
        print(f"[DEBUG] update_recruitment_process called with job_id={job_id}, candidate_email={candidate_email}, status={status}")
        job_document = containers[config['database']['job_description_container_name']].read_item(item=str(job_id), partition_key=str(job_id))
        print(f"[DEBUG] Loaded job_document for job_id={job_id}, candidates={len(job_document.get('candidates', []))}")

        if "candidates" not in job_document:
            print(f"[DEBUG] No candidates found for job_id={job_id}")
            return f"Error: No candidates found for job ID {job_id}."

        updated = False
        for candidate in job_document["candidates"]:
            print(f"[DEBUG] Checking candidate: {candidate.get('email')} (target: {candidate_email})")
            if candidate["email"].lower() == candidate_email.lower():
                print(f"[DEBUG] Found candidate, setting status to {status}")
                if status in valid_statuses:
                    candidate["application_status"] = status
                    candidate["status"] = status
                    updated = True
                else:
                    candidate["application_status"] = "Unknown"
                    candidate["status"] = "Unknown"
                    updated = True
        if updated:
            print(f"[DEBUG] Saving updated job_document for job_id={job_id}")
            containers[config['database']['job_description_container_name']].replace_item(item=job_document["id"], body=job_document)
            print(f"[DEBUG] Status for {candidate_email} updated to '{status}'")
            return f"Success: Status for {candidate_email} updated to '{status}'."
        else:
            print(f"[DEBUG] Candidate with email {candidate_email} not found for job_id={job_id}")
            return f"Error: Candidate with email {candidate_email} not found for job ID {job_id}."
    except Exception as e:
        print(f"[DEBUG] An error occurred: {e}")
        return f"An error occurred: {e}"

def store_application(application_data):
    try:
        application_data["type"] = "application"
        containers[config['database']['application_container_name']].upsert_item(body=application_data)
        print(f"Application data stored successfully for {application_data['id']}")
    except exceptions.CosmosHttpResponseError as e:
        print(f"Failed to store application data: {e}")

def fetch_application(application_id):
    try:
        query = f"SELECT * FROM c WHERE c.type = 'application' AND c.id = '{application_id}'"
        results = list(containers[config['database']['application_container_name']].query_items(query=query, enable_cross_partition_query=True))
        return results[0] if results else None
    except Exception as e:
        print(f"An error occurred while fetching application: {e}")
        return None

def store_job_questionnaire(questionnaire_data):
    try:
        questionnaire_data["type"] = "job_questionnaire"
        print(f"Storing questionnaire data for {questionnaire_data['job_id']}")
        containers[config['database']['job_description_questionnaire_container_name']].upsert_item(body=questionnaire_data)
        print(f"Questionnaire data stored successfully for {questionnaire_data['job_id']}")
    except exceptions.CosmosHttpResponseError as e:
        print(f"Failed to store Questionnaire data: {e}")

def fetch_job_description_questionnaire(job_id):
    try:
        query = f"SELECT * FROM c WHERE c.type = 'job_questionnaire' AND c.job_id = '{job_id}'"
        results = list(containers[config['database']['job_description_questionnaire_container_name']].query_items(query=query, enable_cross_partition_query=True))
        if results:
            print(f"Job description questionnaire fetched successfully for job ID: {job_id}")
            return results[0]
        else:
            print(f"No job description questionnaire found for job ID: {job_id}")
            return None
    except Exception as e:
        print(f"An error occurred while fetching job description questionnaire: {e}")
        return None

def fetch_resume_with_email_and_job(job_id, email):
    try:
        query = """
        SELECT * 
        FROM c
        WHERE IS_DEFINED(c.email) AND c.email = @email AND c.job_id = @job_id AND c.type = 'candidate'
        """
        parameters = [
            {"name": "@email", "value": email},
            {"name": "@job_id", "value": job_id}
        ]
        print(f"Executing query to fetch candidate (type='candidate') for job_id: {job_id}, email: {email}...")
        candidates = containers[config['database']['application_container_name']].query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
        for candidate in candidates:
            print(f"Candidate application fetched successfully! Candidate: {candidate}")
            return candidate  # Return the first matched document
        print("No candidate found for the given email and job_id.")
        return None
    except Exception as e:
        print(f"An error occurred while fetching candidate: {e}")
        return None

def fetch_resume_with_email(email):
    try:
        query = """
        SELECT * 
        FROM c
        WHERE IS_DEFINED(c.email) AND c.email = @email AND c.type = 'candidate'
        """
        parameters = [
            {"name": "@email", "value": email}
        ]

        print(f"Executing query to fetch candidate (type='candidate') for email: {email}...")

        candidates = containers[config['database']['application_container_name']].query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
        
        for candidate in candidates:
            print(f"Candidate application fetched successfully! Candidate: {candidate}")
            return candidate  # Return the first matched document
        
        print("No resume found for the given email.")
        return None
    
    except Exception as e:
        print(f"An error occurred while fetching resume: {e}")
        return None

def fetch_application_by_job_id(job_id):
    try:
        query = """
        SELECT * 
        FROM c
        WHERE c.type = 'application' AND c.job_id = @job_id
        """
        parameters = [{"name": "@job_id", "value": job_id}]
        results = list(containers[config['database']['application_container_name']].query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        if results:
            print(f"Application found for job ID: {job_id}")
            return results[0]
        else:
            print(f"No application found for job ID: {job_id}")
            return None
    except Exception as e:
        print(f"An error occurred while fetching application: {e}")
        return None

def create_application_for_job_id(job_id, job_questionnaire_id):
    try:
        new_application = {
            "job_id": job_id,
            "job_questionnaire_id": job_questionnaire_id,
            "id": f"{job_id}_{job_questionnaire_id}",
            "type": "application"
        }

        containers[config['database']['application_container_name']].create_item(body=new_application)

        print(f"New application created for job ID: {job_id}")
        return new_application

    except Exception as e:
        print(f"An error occurred while creating application: {e}")
        return None

def save_ranking_data_to_cosmos_db(ranking_data, candidate_email, ranking, conversation, resume):
    print("[DEBUG] Entered save_ranking_data_to_cosmos_db")
    print(f"[DEBUG] Arguments: candidate_email={candidate_email}, ranking={ranking}, conversation={str(conversation)[:100]}, resume type={type(resume)}")
    try:
        # --- Validation ---
        if not candidate_email or not ranking_data.get('job_id'):
            print(f"[ERROR] Missing candidate_email or job_id. Skipping save. candidate_email={candidate_email}, job_id={ranking_data.get('job_id')}")
            return "Error: Missing candidate_email or job_id."
        if ranking is None:
            print(f"[ERROR] Ranking is None for candidate_email={candidate_email}, job_id={ranking_data.get('job_id')}. Skipping save.")
            return "Error: Ranking is None."

        # --- Save a flat ranking record for UI ---
        flat_ranking_doc = {
            "id": f"{ranking_data['job_id']}_{candidate_email}",
            "type": "ranking",
            "job_id": ranking_data['job_id'],
            "candidate_email": candidate_email,
            "ranking": ranking,
            "ranked_at": datetime.utcnow().isoformat(),
        }
        try:
            containers[config['database']['ranking_container_name']].upsert_item(flat_ranking_doc)
            print(f"[DEBUG] Flat ranking doc upserted for UI: {flat_ranking_doc}")
        except Exception as e:
            print(f"[ERROR] Failed to upsert flat ranking doc for UI: {e}")

        # --- Retain old logic for backward compatibility ---
        if "candidates" not in ranking_data:
            print("[DEBUG] 'candidates' not in ranking_data, initializing empty list.")
            ranking_data["candidates"] = []

        updated = False
        for candidate in ranking_data["candidates"]:
            if candidate["email"].lower() == candidate_email.lower() and candidate.get("job_id") == ranking_data.get("job_id"):
                print(f"[DEBUG] Updating existing candidate entry for {candidate_email}")
                candidate["ranking"] = ranking
                candidate["conversation"] = conversation
                candidate["resume"] = resume
                candidate["application_status"] = "Applied"
                updated = True
                break
        print(f"[DEBUG] Candidate updated: {updated}")

        if not updated:
            print(f"[DEBUG] Appending new candidate entry for {candidate_email}")
            new_candidate = {
                "email": candidate_email,
                "job_id": ranking_data.get("job_id"),
                "ranking": ranking,
                "conversation": conversation,
                "resume": resume,
                "application_status": "Applied"
            }
            ranking_data["candidates"].append(new_candidate)
        else:
            print(f"[DEBUG] Did not append new candidate, already updated.")

        if "id" in ranking_data:
            print(f"[DEBUG] About to upsert to Cosmos DB: id={ranking_data['id']} candidates_count={len(ranking_data['candidates'])}")
            containers[config['database']['ranking_container_name']].upsert_item(ranking_data)
            print(f"[DEBUG] Ranking data successfully upserted in Cosmos DB for {candidate_email}.")
            print("[DEBUG] Returning success message")
            return f"Success: The candidate with email {candidate_email} has been added."
        else:
            print(f"[DEBUG] Error: No 'id' found in ranking_data, cannot update the document.")
            print("[DEBUG] Returning error message")
            return "Error: No 'id' found in ranking_data, cannot update the document."
    except Exception as e:
        print(f"[ERROR] An error occurred while saving ranking data: {e}")
        import traceback; traceback.print_exc()
        print("[DEBUG] Returning error message")
        return f"An error occurred: {e}"

import re
from azure.cosmos import exceptions

def is_safe_query(query: str) -> bool:
    normalized_query = query.strip().lower()
    
    if not normalized_query.startswith("select"):
        return False

    disallowed_keywords = ["create", "delete", "insert", "update", "drop", "alter", "truncate", "exec"]

    for keyword in disallowed_keywords:
        if re.search(r'\b' + keyword + r'\b', normalized_query):
            return False

    return True

def execute_sql_query(query: str):
    if not is_safe_query(query):
        print("Unsafe query detected. Aborting execution.")
        return None

    try:
        results = list(containers[config['database']['resumes_container_name']].query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return results
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error executing SQL query: {e}")
        return None
