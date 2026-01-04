from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app_v2.database import get_db
from app_v2.feeds import FeedError, get_feed_status, run_govcon_feed, run_rei_feed
from app_v2.utils.logger import get_logger

router = APIRouter(prefix="/feeds", tags=["feeds"])
logger = get_logger(__name__)


@router.post("/run")
def run_feed(
    feed: str = Query(default="govcon", enum=["govcon", "rei"]),
    db: Session = Depends(get_db),
):
    try:
        if feed == "govcon":
            result = run_govcon_feed(db)
        else:
            result = run_rei_feed(db)
        return {"status": "ok", "feed": feed, **result}
    except FeedError as exc:
        logger.error(f"Feed run failed: {exc}")
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Unexpected feed error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal feed error")


@router.get("/status")
def feed_status(db: Session = Depends(get_db)):
    try:
        return {"status": "ok", **get_feed_status(db)}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to load feed status: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load feed status")
