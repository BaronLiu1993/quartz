from github import Github, Auth
import os

token = os.getenv("GITHUB_TOKEN")

def get_github_client():
    auth = Auth.Token(token=token)
    client = Github(auth=auth)
    return client