# src/tools/fix_crack.py
from fastapi import APIRouter
from .repo_write import write_file
from .deploy import deploy

router = APIRouter(prefix="/fix_crack")


@router.post("/")
def fix_crack(path: str, content: str):
    write_file(path, content)
    deploy()
    return {"status": "crack fixed + deployed"}
