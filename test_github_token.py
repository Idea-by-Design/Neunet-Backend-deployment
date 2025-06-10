import os
from github import Github
from dotenv import load_dotenv
load_dotenv()
token = os.getenv("GITHUB_TOKEN")
print("Token loaded:", repr(token))
g = Github(token)
print(g.get_rate_limit())
