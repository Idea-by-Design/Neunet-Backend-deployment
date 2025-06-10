import os
import sys
from azure.cosmos import CosmosClient, exceptions

# Add project root to sys.path to allow direct execution of script
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Initialize containers and config by importing from db_operations
# This ensures db_operations.py runs its global setup code.
from common.utils.config_utils import load_config
from common.database.cosmos.db_operations import containers, config

CANDIDATE_EMAIL = "cynthia@beamjobs.com"
TARGET_JOB_ID = "826051"

def fix_cynthia_links_from_other_apps():
    print(f"Attempting to fix links for candidate {CANDIDATE_EMAIL} in job {TARGET_JOB_ID} by checking other applications.")

    application_container_name = config['database']['application_container_name']
    application_container = containers.get(application_container_name)

    if not application_container:
        print(f"Error: Could not get application_container instance for '{application_container_name}'.")
        return

    # 1. Fetch the target application record by querying for job_id and email
    print(f"Querying for target application record: job_id='{TARGET_JOB_ID}', email='{CANDIDATE_EMAIL}'...")
    # Assuming 'type': 'candidate' might be part of the schema for these records, based on other db_operations
    # If not, the c.type condition can be removed or adjusted.
    query = f"SELECT * FROM c WHERE c.job_id = '{TARGET_JOB_ID}' AND c.email = '{CANDIDATE_EMAIL}'"
    
    target_app_record = None
    try:
        # Partition key is /job_id, so specifying it makes the query more efficient and avoids cross-partition costs if record exists in that partition.
        target_apps = list(application_container.query_items(query=query, partition_key=TARGET_JOB_ID, enable_cross_partition_query=False))
        
        if not target_apps:
            print(f"Target application record not found with job_id='{TARGET_JOB_ID}' and email='{CANDIDATE_EMAIL}' using partition key '{TARGET_JOB_ID}'.")
            # As a fallback, try a cross-partition query, in case the record somehow ended up in a different logical partition (unlikely if PK is job_id)
            print("Attempting cross-partition query as a fallback...")
            target_apps_cross = list(application_container.query_items(query=query, enable_cross_partition_query=True))
            if not target_apps_cross:
                print(f"Target application record also not found with cross-partition query. Cannot proceed.")
                return
            elif len(target_apps_cross) > 1:
                print(f"Warning: Multiple application records found (cross-partition) for email '{CANDIDATE_EMAIL}' and job_id '{TARGET_JOB_ID}'. Using the first one: ID {target_apps_cross[0].get('id')}")
                target_app_record = target_apps_cross[0]
            else:
                target_app_record = target_apps_cross[0]
                print(f"Found target application record (cross-partition). ID: {target_app_record.get('id')}")
        elif len(target_apps) > 1:
            print(f"Warning: Multiple application records found for email '{CANDIDATE_EMAIL}' and job_id '{TARGET_JOB_ID}'. Using the first one: ID {target_apps[0].get('id')}")
            target_app_record = target_apps[0]
        else:
            target_app_record = target_apps[0]
            print(f"Found target application record. ID: {target_app_record.get('id')}")

    except Exception as e:
        print(f"Error querying for target application record: {e}")
        return

    if not target_app_record:
        # This case should be caught by the checks above, but as a safeguard.
        print("Failed to retrieve the target application record after query attempts.")
        return

    candidate_id = target_app_record.get('candidate_id')
    if not candidate_id:
        print(f"Error: Target application record for {CANDIDATE_EMAIL}, job {TARGET_JOB_ID} is missing 'candidate_id'. Cannot find other applications.")
        return
    print(f"Candidate ID for {CANDIDATE_EMAIL} is {candidate_id}")

    # 2. Fetch all other applications for this candidate_id
    print(f"Fetching all applications for candidate_id {candidate_id} from container '{application_container_name}'...")
    source_apps_query = f"SELECT * FROM c WHERE c.candidate_id = '{candidate_id}'"
    
    try:
        all_candidate_applications = list(application_container.query_items(query=source_apps_query, enable_cross_partition_query=True))
    except Exception as e:
        print(f"Error querying applications for candidate_id {candidate_id}: {e}")
        return

    if not all_candidate_applications:
        print(f"No applications found for candidate_id {candidate_id}. Cannot find a source for parsed_resume.")
        # This case should ideally not happen if the target_app_record itself was found, as it's part of this set.
        # However, if it's the *only* one, the loop below won't find a different source.
        pass # Continue to fallback logic

    # 3. Find a suitable source application from other applications
    source_parsed_resume = None
    source_resume_blob_name = None
    found_source_app_id = None

    # Prefer applications that are not the target one and have the necessary data
    # Get the ID of the target record for comparison
    target_record_actual_id = target_app_record.get('id')

    for app in sorted(all_candidate_applications, key=lambda x: x.get('id', ''), reverse=True):
        if app.get('id') == target_record_actual_id:
            continue # Skip the target application itself as a source for now
        
        current_app_parsed_resume = app.get('parsed_resume')
        current_app_resume_blob_name = app.get('resume_blob_name')

        if current_app_parsed_resume and current_app_resume_blob_name:
            source_parsed_resume = current_app_parsed_resume
            source_resume_blob_name = current_app_resume_blob_name
            found_source_app_id = app.get("id")
            print(f"Found suitable source application: ID {found_source_app_id} (job_id: {app.get('job_id')}) with both parsed_resume and resume_blob_name.")
            break 
        elif current_app_parsed_resume and not source_parsed_resume: # If no app with both found yet, take one with at least parsed_resume
            source_parsed_resume = current_app_parsed_resume
            source_resume_blob_name = current_app_resume_blob_name # This might be None
            found_source_app_id = app.get("id")
            print(f"Found source application: ID {found_source_app_id} (job_id: {app.get('job_id')}) with parsed_resume. resume_blob_name is {'present' if source_resume_blob_name else 'missing'}.")
            # Don't break; keep looking for one with both fields if possible

    # 4. Fallback: If no suitable *other* application was found, try the resumes_container
    if not source_parsed_resume and not source_resume_blob_name:
        print(f"Could not find 'parsed_resume' and 'resume_blob_name' in other applications for candidate_id {candidate_id}.")
        print("Falling back to check 'resumes' container...")
        resumes_container_name = config['database'].get('resumes_container_name')
        resumes_container = containers.get(resumes_container_name)

        if resumes_container:
            general_resume_query = f"SELECT * FROM c WHERE c.type = 'resume' AND c.email = '{CANDIDATE_EMAIL}'"
            try:
                general_resumes = list(resumes_container.query_items(query=general_resume_query, enable_cross_partition_query=True))
                if general_resumes:
                    general_resume_data = general_resumes[0]
                    print(f"Found general resume in 'resumes' container. ID: {general_resume_data.get('id')}")
                    # Only use from general_resume if the specific field is better/present
                    if general_resume_data.get('parsed_resume') and not source_parsed_resume:
                        source_parsed_resume = general_resume_data.get('parsed_resume')
                    if general_resume_data.get('resume_blob_name') and not source_resume_blob_name:
                        source_resume_blob_name = general_resume_data.get('resume_blob_name')
                    found_source_app_id = f"resumes_container_item:{general_resume_data.get('id')}" # Indicate source
                else:
                    print(f"No general resume found for {CANDIDATE_EMAIL} in 'resumes' container either.")
            except Exception as e_res:
                print(f"Error querying resumes_container as fallback: {e_res}")
        else:
            print(f"Resumes container '{resumes_container_name}' not available or not configured for fallback.")

    if not source_parsed_resume and not source_resume_blob_name:
        print("No source data found in other applications or in the general resumes container. Cannot fix.")
        return

    # 5. Update target application record if necessary
    updated_fields = []
    needs_update = False

    # Check parsed_resume
    if source_parsed_resume:
        if target_app_record.get('parsed_resume') != source_parsed_resume:
            target_app_record['parsed_resume'] = source_parsed_resume
            updated_fields.append("'parsed_resume'")
            needs_update = True
    elif target_app_record.get('parsed_resume'): # Source is None, but target has something - this shouldn't happen if we want to 'fix' by adding
        pass # Or decide to clear it if that's the intent: target_app_record['parsed_resume'] = None

    # Check resume_blob_name
    if source_resume_blob_name:
        if target_app_record.get('resume_blob_name') != source_resume_blob_name:
            target_app_record['resume_blob_name'] = source_resume_blob_name
            updated_fields.append("'resume_blob_name'")
            needs_update = True
    elif target_app_record.get('resume_blob_name'):
        pass # Source is None, but target has something

    if needs_update:
        print(f"Updating target application {target_record_actual_id} with data from source {found_source_app_id if found_source_app_id else 'unknown'}.")
        try:
            application_container.replace_item(item=target_app_record['id'], body=target_app_record)
            print(f"Successfully updated application record for {CANDIDATE_EMAIL}, job {TARGET_JOB_ID}. Fields updated: {', '.join(updated_fields)}.")
        except Exception as e:
            print(f"Error saving updated application record: {e}")
    else:
        print(f"No updates were necessary for target application {target_app_item_id}.")
        if source_parsed_resume:
            print(f"  Target 'parsed_resume' already matches source or source was not better.")
        else:
            print(f"  No source 'parsed_resume' found to update target.")
        if source_resume_blob_name:
            print(f"  Target 'resume_blob_name' already matches source or source was not better.")
        else:
            print(f"  No source 'resume_blob_name' found to update target.")

if __name__ == "__main__":
    fix_cynthia_links_from_other_apps()
