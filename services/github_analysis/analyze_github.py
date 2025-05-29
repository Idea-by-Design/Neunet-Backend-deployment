import github
from github import Github
import os
from services.common.utils.config_utils import load_config
from services.github_analysis.helper import extract_github_username, fetch_candidate_commits, analyze_contributions_with_llm
from dotenv import load_dotenv

# Load environment variables from .env file in the project directory
from pathlib import Path
# Always load .env from backend root
backend_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(backend_root / ".env")

# Load configuration
config = load_config()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# GitHub authentication using a personal access token
g = Github(GITHUB_TOKEN)


def analyze_github_profile(github_identifier, candidate_email):
    print(f"Analyzing profile for GitHub identifier: {github_identifier}")

    username = extract_github_username(github_identifier)
    user = g.get_user(username)
    repos = user.get_repos()

    analysis_data = {
        "github_url": f"https://github.com/{username}",
        "repositories": []
    }

    for repo in repos:
        if repo.private:
            continue  # Skip private repositories

        print(f"Processing repository: {repo.name}")
        
        try:
            # Check if the repository has commits
            commit_count = repo.get_commits().totalCount
            if commit_count == 0:
                print(f"Skipping empty repository: {repo.name}")
                continue

            # Collecting basic data
            repo_data = {
                "name": repo.name,
                "description": repo.description,
                "language": repo.language,
                "topics": repo.get_topics(),
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "pushed_at": repo.pushed_at.isoformat(),
                "commit_count": commit_count,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "watchers": repo.watchers_count
            }

            # Fetch commits by the candidate
            candidate_commits = fetch_candidate_commits(repo, username)

            # If the candidate has commits in this repository, analyze them
            if candidate_commits:
                # Analyzing contribution with LLM
                contribution_insights = analyze_contributions_with_llm(repo, candidate_email, candidate_commits)
                repo_data["contribution_insights"] = contribution_insights

            analysis_data["repositories"].append(repo_data)
        
        except github.GithubException as e:
            # Skip repositories with errors like empty repositories
            if e.status == 409 and "Git Repository is empty" in e.data['message']:
                print(f"Skipping repository {repo.name} because it is empty.")
                continue
            else:
                print(f"Error processing repository {repo.name}: {e}")
                continue  # Skip this repo and proceed with the next one

    print(f"Analysis complete for {github_identifier}")
    return analysis_data

