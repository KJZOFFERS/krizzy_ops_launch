import os

import uvicorn
from src.app import app  # FastAPI app object in src/app.py


def get_port() -> int:
    """
    Resolve the port to run on.

    Railway sets PORT automatically. Default to 8000 for local dev.
    """
    port_str = os.environ.get("PORT", "8000")
    try:
        return int(port_str)
    except ValueError:
        # Hard fail if PORT is misconfigured instead of silently picking a port
        raise RuntimeError(f"Invalid PORT value: {port_str!r}. Must be an integer.")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=get_port(),
    )
