import openai
from openai import AzureOpenAI
import os
import requests

from dotenv import load_dotenv
from pathlib import Path

# Always load the .env from the neunet_ai_services project root, regardless of where the server is started
backend_root = Path(__file__).resolve().parent.parent.parent  # neunet_ai_services directory
env_path = backend_root / ".env"
print("[DEBUG] .env path:", env_path)
print("[DEBUG] .env exists:", env_path.exists())
load_dotenv(env_path)

# DEBUG: Print loaded environment variables
print("AZURE_OPENAI_API_KEY:", os.getenv("AZURE_OPENAI_API_KEY"))
print("AZURE_OPENAI_ENDPOINT:", os.getenv("AZURE_OPENAI_ENDPOINT"))
print("api_version:", os.getenv("api_version"))
print("deployment_name:", os.getenv("deployment_name"))

client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version=os.getenv("api_version"))

model= os.getenv("deployment_name")

def generate_description(data):
    # Ensure all required keys for prompt formatting are present
    required_fields = [
        'title', 'company_name', 'location', 'estimated_pay', 'type', 'time_commitment',
        'job_level', 'description', 'requirements', 'benefits', 'job_id'
    ]
    # Set defaults for missing fields
    for field in required_fields:
        if field not in data or data[field] is None:
            if field == 'estimated_pay':
                data[field] = "Not specified"
            elif field == 'job_level':
                data[field] = "Not specified"
            elif field == 'benefits':
                data[field] = ""
            else:
                data[field] = ""
    # Also ensure both 'title' and 'job_title' are present for prompt formatting
    if "title" in data and "job_title" not in data:
        data["job_title"] = data["title"]
    if "job_title" in data and "title" not in data:
        data["title"] = data["job_title"]

    # Debug: Print the data dictionary before formatting
    print("[DEBUG] Data passed to prompt template:", data)

    # Load the initial prompt template
    prompt_template = load_prompt()
    print("[DEBUG] Prompt template before formatting:\n", prompt_template)

    try:
        # Finalize the prompt with the available data
        final_prompt = prompt_template.format(**data)
    except KeyError as e:
        print("[ERROR] KeyError during prompt formatting! Missing key:", e)
        print("[ERROR] Data dictionary:", data)
        raise

    # Call the OpenAI API to generate the job description
    generated_description = call_openai_api(final_prompt)
    return generated_description

def load_prompt():
    from pathlib import Path
    def find_prompt_upwards(filename="prompts/generate_job_description.txt", start_path=None):
        import os
        if start_path is None:
            start_path = Path(__file__).resolve().parent
        current = start_path
        while True:
            candidate = current / filename
            if candidate.exists():
                return candidate
            if current.parent == current:
                break
            current = current.parent
        return None

    prompt_path = find_prompt_upwards()
    print("PROMPT PATH:", prompt_path)
    print("PROMPT EXISTS:", prompt_path.exists() if prompt_path else False)
    if not prompt_path:
        raise FileNotFoundError("Could not find prompts/generate_job_description.txt upwards from " + str(Path(__file__).resolve().parent))
    with open(prompt_path, 'r') as file:
        return file.read()


def check_missing_fields(data):
    required_fields = [
        'title', 'company_name', 'location', 'type', 
        'time_commitment', 'description', 'requirements'
    ]
    missing = {field: None for field in required_fields if not data.get(field)}
    return missing

def generate_questions_for_missing_fields(missing_fields):
    questions = {}
    if 'title' in missing_fields:
        questions['title'] = "Please provide the title of the job position."
    if 'company_name' in missing_fields:
        questions['company_name'] = "Please provide the company or organization's name."
    if 'location' in missing_fields:
        questions['location'] = "Please provide the job location."
    if 'type' in missing_fields:
        questions['type'] = "Is this job remote, hybrid, or onsite?"
    if 'time_commitment' in missing_fields:
        questions['time_commitment'] = "Is this a full-time, part-time, or contract position?"
    if 'description' in missing_fields:
        questions['description'] = "Please provide a detailed description of the roles and responsibilities."
    if 'requirements' in missing_fields:
        questions['requirements'] = "Please list the key skills and qualifications required for the job."
    if 'estimated_pay' in missing_fields:
        questions['estimated_pay'] = "Please provide the estimated pay range for this position."
    if 'job_level' in missing_fields:
        questions['job_level'] = "Please specify the job level (e.g., entry-level, junior, middle, senior)."
    # Add more questions for each missing field as needed
    return questions

def gather_missing_info(questions, job_id):
    responses = {}
    for field, question in questions.items():
        # Here, instead of a placeholder, you would integrate with your chatbot or API to get this data.
        # This could involve sending an HTTP request to a service that handles gathering recruiter inputs.
        response = get_info_from_chatbot_or_api(job_id, field, question)
        responses[field] = response
    return responses

def fill_missing_fields_with_defaults(data):
    # Provide default values for any missing fields
    defaults = {
        'job_level': "Not specified",
        'estimated_pay': "Not specified",
        'benefits': "",
        'company_culture': "",
        'interview_process': "",
        'growth_opportunities': "",
        'tech_stack': ""
    }
    for field, default_value in defaults.items():
        if not data.get(field):
            data[field] = default_value
    return data

def call_openai_api(prompt):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are an AI assistant that helps generate comprehensive and compelling job descriptions based on the provided data.",
                    "role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# def get_info_from_chatbot_or_api(job_id, field, question):
#     # Example: Call an API that interacts with the recruiter to get missing information
#     # This is a placeholder for your actual implementation

#     api_url = os.getenv('INFO_GATHERING_API_URL')  # Ensure you have this environment variable set
#     headers = {'Authorization': f"Bearer {os.getenv('API_TOKEN')}"}

#     payload = {
#         'job_id': job_id,
#         'field': field,
#         'question': question
#     }

#     response = requests.post(api_url, json=payload, headers=headers)
#     response_data = response.json()

#     return response_data.get('answer')


def get_info_from_chatbot_or_api(job_id, field, question):
    # Mock interaction for local testing
    mock_responses = {
        'title': "Software Engineer",
        'company_name': "TechCorp Inc.",
        'location': "San Francisco, CA",
        'type': "remote",
        'time_commitment': "full-time",
        'description': "Develop and maintain web applications.",
        'requirements': "Experience with Python and JavaScript.",
        'estimated_pay': "$100,000 - $120,000",
        'job_level': "Junior"
    }
    print(f"Question: {question}")
    return mock_responses.get(field, "Default Answer")
