# src/tools/deploy.py
import os
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/deploy")
HOOK = os.getenv("RAILWAY_DEPLOY_HOOK")


@router.post("/")
def deploy():
    if not HOOK:
        raise HTTPException(500, "Missing RAILWAY_DEPLOY_HOOK")

    r = requests.post(HOOK)
    if r.status_code >= 300:
        raise HTTPException(500, "Deploy failed")

    return {"status": "deployment triggered"}
