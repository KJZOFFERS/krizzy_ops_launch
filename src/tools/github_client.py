# src/tools/github_client.py
import os
import base64
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPO")  # "username/repo"
BRANCH = "main"


class GitHubClient:
    def __init__(self):
        if not GITHUB_TOKEN or not REPO:
            raise RuntimeError("Missing GitHub env vars.")

        self.base = f"https://api.github.com/repos/{REPO}"

    def get_file(self, path):
        r = requests.get(
            f"{self.base}/contents/{path}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"}
        )
        r.raise_for_status()
        return r.json()

    def update_file(self, path, content, sha):
        r = requests.put(
            f"{self.base}/contents/{path}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
            json={
                "message": f"Update {path}",
                "content": base64.b64encode(content.encode()).decode(),
                "sha": sha,
                "branch": BRANCH
            }
        )
        r.raise_for_status()
        return r.json()

    def create_file(self, path, content):
        r = requests.put(
            f"{self.base}/contents/{path}",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
            json={
                "message": f"Create {path}",
                "content": base64.b64encode(content.encode()).decode(),
                "branch": BRANCH
            }
        )
        r.raise_for_status()
        return r.json()
