import os
from services.resume_ranking.job_description_questionnaire.jd_questionnaire_generator import generate_questionnaire, save_questionnaire
from common.database.cosmos.db_operations import fetch_job_description, store_job_questionnaire
import json
import datetime



def read_file_to_string(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except IOError:
        print(f"Error: There was an issue reading the file at {file_path}.")
        return None
    
    
def main():
    
    # jd = fetch_job_description("123456")
    # print(jd)
    id = 123486
    # Call DB for Job Description
    job_description = fetch_job_description(id)

    # Generate questionnaire using the job description
    print("Generating questionnaire...")
    raw_response = generate_questionnaire(job_description)

        
    # Store output in DB
    start_idx = raw_response.find("{")
    end_idx = raw_response.rfind("}")
    try:
        json_data = json.loads(raw_response[start_idx:end_idx+1])
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        raise
    print(json_data)
    
    json_data['job_id'] = id
    
    #create unique id
    # Get the current date and time in a specific format
    current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    # Create a unique ID by concatenating 'some_variable' with the date and time
    unique_id = f"{id}_{current_time}"

    json_data['id'] = unique_id
    store_job_questionnaire(json_data)

    # Confirm completion
    print(f"Questionnaire saved.")

if __name__ == '__main__':
    main()
    # way to run: python -m services.resume_ranking.tests.test_jd_question_maker 
