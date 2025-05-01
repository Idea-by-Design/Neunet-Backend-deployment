from azure.cosmos import CosmosClient, PartitionKey, exceptions
from common.utils.config_utils import load_config
from datetime import datetime
import ast


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

def upsert_candidate(candidate_data):
    """
    Upsert a candidate application into the database.
    """
    try:
        print(f"Upserting candidate application for job {candidate_data['job_id']}")
        print("Candidate data to upsert:", candidate_data)
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
        
        print(f"Found {len(candidates)} candidates for job {job_id}")
        return candidates
        
    except Exception as e:
        print(f"An error occurred while fetching candidates: {e}")
        return []

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
    try:
        query = """
        SELECT c.email, c.links.gitHub AS github
        FROM c
        WHERE c.type = 'resume' AND IS_DEFINED(c.links.gitHub)
        """
        print("Executing query to fetch candidates with GitHub links...")
        candidates = list(containers[config['database']['resumes_container_name']].query_items(query=query, enable_cross_partition_query=True))
        print(f"Fetched {len(candidates)} candidates.")
        for candidate in candidates:
            print(candidate)
        return candidates
    except Exception as e:
        print(f"An error occurred while fetching candidates: {e}")
        return []

def store_github_analysis(analysis_data):
    try:
        analysis_data["type"] = "github_analysis"
        print(f"Storing analysis data for {analysis_data['email']}")
        containers[config['database']['github_container_name']].upsert_item(body=analysis_data)
        print(f"GitHub analysis data stored successfully for {analysis_data['email']}")
    except exceptions.CosmosHttpResponseError as e:
        print(f"Failed to store GitHub analysis data: {e}")

def fetch_github_analysis(email):
    try:
        query = f"SELECT * FROM c WHERE c.type = 'github_analysis' AND c.email = '{email}'"
        results = list(containers[config['database']['github_container_name']].query_items(query=query, enable_cross_partition_query=True))
        return results[0] if results else None
    except Exception as e:
        print(f"An error occurred while fetching GitHub analysis: {e}")
        return None

def store_candidate_ranking(job_id, candidate_email, ranking):
    try:
        ranking_data = {
            "id": f"{job_id}_{candidate_email}",
            "job_id": job_id,
            "candidate_email": candidate_email,
            "ranking": ranking,
            "ranked_at": datetime.utcnow().isoformat(),
            "type": "ranking"
        }
        containers[config['database']['ranking_container_name']].upsert_item(ranking_data)
        print(f"Ranking stored successfully for job {job_id} and candidate {candidate_email}")
    except exceptions.CosmosHttpResponseError as e:
        print(f"Failed to store ranking: {e}")

def fetch_candidate_rankings(job_id):
    try:
        query = f"SELECT c.candidate_email, c.ranking, c.ranked_at FROM c WHERE c.type = 'ranking' AND c.job_id = '{job_id}'"
        rankings = list(containers[config['database']['ranking_container_name']].query_items(query=query, enable_cross_partition_query=True))
        return {r['candidate_email']: {'ranking': r['ranking'], 'ranked_at': r['ranked_at']} for r in rankings}
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
        "Withdrawn"
    ]

    try:
        job_document = containers[config['database']['job_description_container_name']].read_item(item=str(job_id), partition_key=str(job_id))
        
        if "candidates" not in job_document:
            return f"Error: No candidates found for job ID {job_id}."

        for candidate in job_document["candidates"]:
            if candidate["email"].lower() == candidate_email.lower():  
                if new_status in valid_statuses:
                    candidate["application_status"] = new_status
                    containers[config['database']['job_description_container_name']].replace_item(item=job_document["id"], body=job_document)
                    return f"Success: Application status for {candidate_email} updated to '{new_status}'."
                else:
                    candidate["application_status"] = "Unknown"
                    containers[config['database']['job_description_container_name']].replace_item(item=job_document["id"], body=job_document)
                    return f"Error: Invalid status '{new_status}' provided. Status set to 'Unknown'."

        return f"Error: Candidate with email {candidate_email} not found for job ID {job_id}."
    
    except Exception as e:
        print(f"An error occurred: {e}")
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
        query = f"SELECT * FROM c WHERE c.type = 'job_questionnaire' AND c.job_id = {job_id}"
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
    try:
        if "candidates" not in ranking_data:
            ranking_data["candidates"] = []

        for candidate in ranking_data["candidates"]:
            if candidate["email"].lower() == candidate_email.lower():  
                return f"Error: The candidate with email {candidate_email} has already applied."

        new_candidate = {
            "email": candidate_email,
            "ranking": ranking,
            "conversation": conversation,
            "resume": resume,
            "application_status": "Applied"
        }
        ranking_data["candidates"].append(new_candidate)

        if "id" in ranking_data:
            containers[config['database']['ranking_container_name']].replace_item(item=ranking_data["id"], body=ranking_data)
            print(f"Ranking data successfully updated in Cosmos DB for {candidate_email}.")
            return f"Success: The candidate with email {candidate_email} has been added."
        else:
            return "Error: No 'id' found in ranking_data, cannot update the document."
    except Exception as e:
        print(f"An error occurred while saving ranking data: {e}")
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
