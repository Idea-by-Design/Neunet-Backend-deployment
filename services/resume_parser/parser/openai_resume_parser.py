import openai
from openai import AzureOpenAI
import json

import os

from dotenv import load_dotenv

# Load environment variables from .env file in the project directory
load_dotenv(dotenv_path=".env")

client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version=os.getenv("api_version"))

model= os.getenv("deployment_name")

def parse_resume_json(resume_text, links=None):
    if resume_text is None:
        raise ValueError("resume_text cannot be None")
    if not isinstance(resume_text, str):
        raise ValueError("resume_text must be a string")

    print("[DEBUG] resume_text sent to OpenAI:\n", resume_text)
    print("[DEBUG] links sent to OpenAI:\n", links)
    
    prompt = f"""
    Extract the following information from the resume text.
    
    - name
        - Extract the candidate's full name exactly as written at the very top of the resume or in the header. This is almost always the first and largest text. Do not use initials or abbreviations; use the complete name (e.g., "May Riley"). If the name is present anywhere in the first few lines, extract it verbatim, even if it looks like a heading.
    - email
    - secondary email
    - phone number
    - secondary phone number
    - location
    - links
        - linkedIn (If a LinkedIn URL is present anywhere, extract the entire URL including the username or profile ID, e.g., "linkedin.com/in/m.riley". Do not truncate or omit the username. If the LinkedIn URL is split across lines or has extra spaces, reconstruct it as a single URL.)
        - gitHub
        - website
        - other
    - email
    - secondary email
    - phone number
    - secondary phone number
    - location
    - links
        - linkedIn (If a LinkedIn URL is present anywhere, extract the entire URL including the username or profile ID, e.g., "linkedin.com/in/m.riley". Do not truncate or omit the username.)
        - gitHub
        - website
        - other
    - skills (comma-separated list; if a dedicated "Skills" section is not present, extract relevant skills from the experience, summary, and profile sections and list them here)

    Example:
    Resume Text:
    \"\"\"
    John Doe
    123 Main Street, New York, NY | (123) 456-7890 | john.doe@email.com | https://www.linkedin.com/in/johndoe
    ...
    \"\"\"
    Expected Output:
    {{
      "name": "John Doe",
      "email": "john.doe@email.com",
      ...
      "links": {{
        "linkedIn": "https://www.linkedin.com/in/johndoe",
        ...
      }},
      ...
    }}

    - skills (comma-separated list)
    - education 
        - education 1 
            - degree
            - institute
            - major
            - minor
            - start (format: MM/YYYY)
            - end (format: MM/YYYY or "Present" if currently enrolled)
            - location
        - education 2 similar to above and so on
    - work experience (this can include internships, etc.)
        - experience 1
            - organization
            - position
            - role description
            - start date (format: MM/YYYY)
            - end date (format: MM/YYYY or "Present" if currently working)
            - location
        - experience 2 similar to above and so on
    - projects
        - project 1
            - title
            - description
        - project 2 similar to above and so on
    - co-curricular activities
    - publications 
        - publication 1
            - title
            - link,
            - description
        - publication 2 similar to above and so on
    - achievements
    - certifications
    - references
    - languages
    - hobbies
    - keywords (comma-separated list; analyse the resume text to detect technical and non-technical skills of the candidate and  tools, technologies, etc. the candidate appears to be proficient in; list should be exhaustive)

    Resume Text:
    {resume_text}
    {links}


    Also, extract any additional information that you think is relevant and not covered in the above points.
    Use the exact keys and sub-key etc naming convention as described above. 
    If the information is not present in the resume then set the value to an empty string or null-value.
    If skills are not found or clearly incicated by a heading, then pick the skills as per the resume and add them to "keywords" tag.
    "keywordes" tag cannot be empty. Analyse the resume to best of your ability and provide the keywords. Make sure to include both technical and non-technical skills. Examples of non-technical skills are leadership, time management, planning, decision making, strategic thinking etc). Be exhaustive.
    Provide the extracted information in JSON format. Return only the JSON string.
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a resume information extractor. You have been provided with the data in the resume and your job is to understand the data and extract the required information."},
            {"role": "system", "content": "When given the resume text, process and understand the data throughly and then proceed to present the extracted information in JSON format."},
            {"role": "user", "content": prompt}
        ],
        stop=None,
    )

    raw_response = response.choices[0].message.content
    
    print("[DEBUG] raw_response from OpenAI:\n", raw_response)

    start_idx = raw_response.find("{")
    end_idx = raw_response.rfind("}")

    try:
        json_data = json.loads(raw_response[start_idx:end_idx+1])
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        raise
    
    return json_data
