import os
import openai
from openai import AzureOpenAI
import json
from dotenv import load_dotenv

# Load environment variables from .env file in the project directory
from pathlib import Path
# Always load .env from backend root
backend_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(backend_root / ".env")

from common.database.cosmos import db_operations


client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), api_version=os.getenv("api_version"))

model= os.getenv("deployment_name")

# Function to generate a questionnaire using GPT-4o-mini
def generate_questionnaire(job_description):
    prompt = f"""
You are an expert recruitment consultant tasked with creating a detailed and structured questionnaire based on the provided job description. The goal is to evaluate candidate resumes by examining key qualifications, skills, career experiences, and overall fit for the role. Your objective is to ensure a comprehensive evaluation while minimizing subconscious bias by avoiding personal information such as names, gender, or other identifiers.

Key Considerations:
- CRITICAL: Ensure that EACH and EVERY required skill, tool, and responsibility mentioned in the job description is covered by at least one question.
- After generating the questionnaire, review the job description again and verify that no key requirement has been omitted.
- Take each item from key_responsibilities, qualifications, and skills_and_competencies and ensure that each skill, tool, responsibility, or experience needed has its own separate question in the appropriate category.
- Critical technical requirements such as frameworks, tools, or libraries should always be explicitly addressed with follow-up questions asking for real-world applications.

Questionnaire Structure:
Generate questions for the following categories:
1. Core Technical Skills
2. Development, Engineering, or System Optimization Experience
3. Problem-Solving and Analytical Thinking
4. Work History and Career Progression
5. Education and Certifications
6. Industry and Domain Expertise
7. Transferable Skills and Emerging Technologies
8. Leadership, Mentorship, and Career Impact
9. Location and Work Eligibility
10. Cultural Fit and Adaptability
11. Diversity and Inclusion

For each category:
- Create specific questions that directly assess the skills and requirements mentioned in the job description.
- Ensure that each question clearly evaluates whether the candidate has the required experience, skills, or characteristics.
- Focus on how, where, and to what extent the candidate has demonstrated these skills in past roles.

Question Format:
Each question should follow this format:
- Question: Does the candidate have experience with [specific task, tool, or skill] as required by the job description? How has the candidate demonstrated [specific skill, experience, or role] in past roles?
- Weight: Assign a weight from 1-5 (1 being low priority, 5 being critical) to each question, reflecting its importance based on the job description.
- Scoring: Leave this field blank so it can be filled in after evaluating each candidate.

Final Check:
After generating the questionnaire, perform these steps:
1. Review the entire job description again.
2. Create a checklist of all mentioned skills, tools, responsibilities, and requirements.
3. Cross-check each item on the checklist against the generated questions.
4. If any item is not covered, add a new question to address it in the appropriate category.

Additional considerations:
- Avoid using any personal information that could introduce subconscious bias.
- Weight the questions appropriately based on the job description, focusing on the most critical qualifications and experiences for the role.

Output Format:
- The responses should be formatted in JSON, with each question categorized and structured as follows:
  - "questionnaire": {{
      "Core Technical Skills": [{{
          "question": "Does the candidate have experience with...?",
          "weight": 5,
          "scoring": ""
      }}],
      ...
  }}

Generate a structured questionnaire that comprehensively evaluates candidates for the role, ensuring each question is specific, relevant, and aligned with the job description. Remember to cover ALL skills and requirements mentioned in the job description.

Here is the job description:
{job_description}
"""




    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert recruitment consultant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,  # Controlled randomness
        max_tokens=4096  # Adjust based on expected response length
    )

    return completion.choices[0].message.content.strip()

# Function to save the generated LLM response in a plain text file
def save_questionnaire(questionnaire, output_folder, output_filename):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    output_path = os.path.join(output_folder, output_filename)

    # Save the LLM response to a plain text file
    with open(output_path, 'w') as txt_file:
        txt_file.write(questionnaire)

    return output_path
