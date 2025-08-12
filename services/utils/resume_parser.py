import json
import re
import logging

def extract_linkedin_github_from_resume(resume_data):
    """
    Extract LinkedIn and GitHub URLs from resume data in various formats.
    
    Args:
        resume_data: Dictionary or string containing resume data
        
    Returns:
        tuple: (linkedin_url, github_url)
    """
    linkedin = ""
    github = ""
    
    # If resume_data is a string, try to parse it as JSON
    if isinstance(resume_data, str):
        try:
            resume_data = json.loads(resume_data)
        except json.JSONDecodeError:
            logging.warning("Could not parse resume_data as JSON")
            return linkedin, github
    
    if not isinstance(resume_data, dict):
        return linkedin, github
    
    # Check in contact section
    if "contact" in resume_data and isinstance(resume_data["contact"], dict):
        linkedin = resume_data["contact"].get("linkedin", "")
        github = resume_data["contact"].get("github", "")
    
    # Check in profiles section (common in parsed resumes)
    if not linkedin or not github:
        if "profiles" in resume_data and isinstance(resume_data["profiles"], list):
            for profile in resume_data["profiles"]:
                if isinstance(profile, dict):
                    if "network" in profile and "url" in profile:
                        if profile["network"].lower() == "linkedin":
                            linkedin = profile["url"]
                        elif profile["network"].lower() == "github":
                            github = profile["url"]
    
    # Check in basics section (JSON Resume format)
    if not linkedin or not github:
        if "basics" in resume_data and isinstance(resume_data["basics"], dict):
            if "profiles" in resume_data["basics"] and isinstance(resume_data["basics"]["profiles"], list):
                for profile in resume_data["basics"]["profiles"]:
                    if isinstance(profile, dict):
                        if "network" in profile and "url" in profile:
                            if profile["network"].lower() == "linkedin":
                                linkedin = profile["url"]
                            elif profile["network"].lower() == "github":
                                github = profile["url"]
    
    # Direct properties
    if not linkedin and "linkedin" in resume_data:
        linkedin = resume_data["linkedin"]
    if not github and "github" in resume_data:
        github = resume_data["github"]
    
    # Check for URLs in text fields that might contain LinkedIn/GitHub links
    if not linkedin or not github:
        # Pattern for LinkedIn URLs
        linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/(?:in|profile)/[\w\-]+/?'
        # Pattern for GitHub URLs
        github_pattern = r'https?://(?:www\.)?github\.com/[\w\-]+/?'
        
        # Function to search for patterns in all string values
        def search_patterns_in_dict(d, depth=0):
            nonlocal linkedin, github
            if depth > 3:  # Limit recursion depth
                return
            
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, str):
                        if not linkedin:
                            linkedin_match = re.search(linkedin_pattern, v)
                            if linkedin_match:
                                linkedin = linkedin_match.group(0)
                        
                        if not github:
                            github_match = re.search(github_pattern, v)
                            if github_match:
                                github = github_match.group(0)
                    elif isinstance(v, (dict, list)):
                        search_patterns_in_dict(v, depth + 1)
            elif isinstance(d, list):
                for item in d:
                    search_patterns_in_dict(item, depth + 1)
        
        # Search for patterns in the resume data
        search_patterns_in_dict(resume_data)
    
    return linkedin, github
