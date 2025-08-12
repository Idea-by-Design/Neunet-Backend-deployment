#!/usr/bin/env python3
"""
Script to update the WebSocket handler in main.py to use the resume parser utility.
"""
import re

# Read the current main.py file
with open('main.py', 'r') as f:
    content = f.read()

# Define the pattern to search for
pattern = r"""                                    # Extract LinkedIn and GitHub links if available
                                    linkedin = ""
                                    github = ""
                                    
                                    # Try to get resume data
                                    if "resume_data" in candidate_data and candidate_data\["resume_data"\]:
                                        resume_data = candidate_data\["resume_data"\]
                                        
                                        # Check if it's a string that needs to be parsed
                                        if isinstance\(resume_data, str\):
                                            try:
                                                resume_data = json\.loads\(resume_data\)
                                            except json\.JSONDecodeError:
                                                logging\.warning\(f"\[WebSocket\] Could not parse resume_data as JSON"\)
                                        
                                        # Extract LinkedIn and GitHub using the same logic as in multiagent_assistant\.py
                                        if isinstance\(resume_data, dict\):
                                            # Check in contact section
                                            if "contact" in resume_data and isinstance\(resume_data\["contact"\], dict\):
                                                linkedin = resume_data\["contact"\]\.get\("linkedin", ""\)
                                                github = resume_data\["contact"\]\.get\("github", ""\)
                                            
                                            # Direct properties
                                            if not linkedin and "linkedin" in resume_data:
                                                linkedin = resume_data\["linkedin"\]
                                            if not github and "github" in resume_data:
                                                github = resume_data\["github"\]"""

# Define the replacement
replacement = """                                    # Extract LinkedIn and GitHub links using our utility function
                                    from services.utils.resume_parser import extract_linkedin_github_from_resume
                                    
                                    linkedin = ""
                                    github = ""
                                    
                                    # Try to get resume data
                                    if "resume_data" in candidate_data and candidate_data["resume_data"]:
                                        resume_data = candidate_data["resume_data"]
                                        linkedin, github = extract_linkedin_github_from_resume(resume_data)
                                        logging.info(f"[WebSocket] Extracted LinkedIn: {bool(linkedin)}, GitHub: {bool(github)} from resume data")"""

# Replace the pattern with our new code
updated_content = re.sub(pattern, replacement, content)

# Write the updated content back to the file
with open('main.py', 'w') as f:
    f.write(updated_content)

print("Successfully updated main.py to use the resume parser utility.")
