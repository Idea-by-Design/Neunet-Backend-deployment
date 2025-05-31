import openai
from openai import AzureOpenAI
import json

import os

from dotenv import load_dotenv

# Load environment variables from .env file in the project directory
from pathlib import Path
# Always load .env from backend root
backend_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(backend_root / ".env")


def extract_github_username(github_identifier):
    """ Extracts the GitHub username from a URL or returns the identifier if it's already a username. """
    if github_identifier.startswith("https://github.com/"):
        return github_identifier.split('/')[-1]
    return github_identifier

def fetch_candidate_commits(repo, username):
    """ Fetches commits from the repository authored by the specified GitHub username. """
    commits = repo.get_commits()
    candidate_commits = [commit.commit.message for commit in commits if commit.author and commit.author.login == username]
    
    return candidate_commits

def analyze_contributions_with_llm(repo, candidate_email, candidate_commits):
    """ Uses an LLM to analyze the candidate's contributions. """
    from openai import AzureOpenAI
    # Initialize the client only when needed
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("api_version")
    )
    model = os.getenv("deployment_name")
    # Prepare data for LLM
    context = f"""
    Repository Name: {repo.name}
    Repository Description: {repo.description}
    Candidate's Commit Messages: {candidate_commits}
    Candidate's Email: {candidate_email}
    """

    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are a github repository analyzer. You have been provided with the data in the repository and the candidate's commit messages. Your job is to understand the data and provide insights on the candidate's role, responsibilities, and impact based on their commits."},
                {"role": "system", "content": "The anakysis should be of short to medium length and should cover the key aspects of the candidate's contributions. Please provide the insights in a clear and concise manner. Do not "},
                {"role": "user", "content": context}
                ],
        stop=None,
    )
    
    return response.choices[0].message.content