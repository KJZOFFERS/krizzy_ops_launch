from fastapi import APIRouter
from src.tools.github_client import get_github_client

router = APIRouter()

@router.post("/repo/write")
async def write_to_repo(path: str, content: str):
    client = get_github_client()
    if client is None:
        return {"error": "GitHub not configured"}
    return client.write_file(path, content)

