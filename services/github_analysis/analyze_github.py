import github
from github import Github
import os
from common.utils.config_utils import load_config
from services.github_analysis.helper import extract_github_username, fetch_candidate_commits, analyze_contributions_with_llm
from dotenv import load_dotenv

# Load environment variables from .env file in the project directory
from pathlib import Path
# Always load .env from backend root
backend_root = Path(__file__).resolve().parent.parent.parent
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
    repos = list(user.get_repos())

    # Efficient total repo and commit counting
    total_repos = 0
    total_commits = 0
    repo_commit_counts = []
    repo_data_list = []

    for repo in repos:
        if repo.private:
            continue  # Skip private repositories
        try:
            commit_count = repo.get_commits().totalCount
        except Exception as e:
            print(f"Error fetching commit count for {repo.name}: {e}")
            continue
        if commit_count == 0:
            continue
        # Always count towards totals if public and non-empty
        total_repos += 1
        total_commits += commit_count
        if commit_count > 10000:
            print(f"Large repository {repo.name} (commits: {commit_count}) counted in totals, but excluded from detailed analysis.")
            continue  # Do not include in detailed/top-5 analysis
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
        # Always include contribution_insights
        if candidate_commits:
            contribution_insights = analyze_contributions_with_llm(repo, candidate_email, candidate_commits)
        else:
            contribution_insights = None
        repo_data["contribution_insights"] = contribution_insights
        repo_data_list.append(repo_data)

    # Select top 5 repositories by most recent activity (pushed_at)
    top_repos = sorted(repo_data_list, key=lambda r: r["pushed_at"], reverse=True)[:5]

    analysis_data = {
        "github_url": f"https://github.com/{username}",
        "total_repositories": total_repos,
        "total_commits": total_commits,
        "repositories": top_repos
    }
    print(f"Analysis complete for {github_identifier}")
    return analysis_data
