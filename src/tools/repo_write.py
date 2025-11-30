# src/tools/repo_write.py
from fastapi import APIRouter, HTTPException
from .github_client import GitHubClient
from .validator import validate_path, validate_python
from .tests_runner import run_tests

router = APIRouter(prefix="/repo_write")
client = GitHubClient()


@router.post("/")
def write_file(path: str, content: str):
    validate_path(path)
    if path.endswith(".py"):
        validate_python(content)

    try:
        info = client.get_file(path)
        sha = info["sha"]
        client.update_file(path, content, sha)
    except Exception:
        client.create_file(path, content)

    code, logs = run_tests()
    if code != 0:
        raise HTTPException(500, f"Tests failed:\n{logs}")

    return {"status": "ok", "path": path}
