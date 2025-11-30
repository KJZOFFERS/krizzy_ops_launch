# src/tools/repo_diff.py
import difflib
import base64
from fastapi import APIRouter, HTTPException
from .github_client import GitHubClient
from .validator import validate_path, validate_python
from .tests_runner import run_tests

router = APIRouter(prefix="/repo_diff")
client = GitHubClient()


def apply_diff(original, patch):
    patched = list(difflib.restore(patch.splitlines(), 2))
    return "\n".join(patched)


@router.post("/")
def apply_repo_diff(path: str, diff: str):
    validate_path(path)

    info = client.get_file(path)
    sha = info["sha"]

    original = base64.b64decode(info["content"]).decode()
    new_content = apply_diff(original, diff)

    if path.endswith(".py"):
        validate_python(new_content)

    client.update_file(path, new_content, sha)

    code, logs = run_tests()
    if code != 0:
        raise HTTPException(500, f"Tests failed:\n{logs}")

    return {"status": "ok", "path": path}
