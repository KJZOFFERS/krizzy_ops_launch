# src/tools/github_client.py
import os
import base64
import requests

class GitHubClient:
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        owner = os.getenv("GITHUB_REPO_OWNER")
        repo = os.getenv("GITHUB_REPO_NAME")

        if not token or not owner or not repo:
            raise RuntimeError("Missing GitHub env vars.")

        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }

    def write_file(self, path: str, content: str):
        url = f"{self.base_url}/contents/{path}"

        encoded = base64.b64encode(content.encode()).decode()
        data = {
            "message": f"Update {path}",
            "content": encoded
        }

        r = requests.put(url, json=data, headers=self.headers)
        return r.json()


def get_github_client():
    try:
        return GitHubClient()
    except Exception:
        return None
