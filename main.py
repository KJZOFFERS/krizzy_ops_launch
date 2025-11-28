import os

import uvicorn
from src.app import app  # FastAPI app object in src/app.py


def get_port() -> int:
    port_str = os.environ.get("PORT", "8000")
    try:
        return int(port_str)
    except ValueError:
        raise RuntimeError(f"Invalid PORT value: {port_str!r}. Must be an integer.")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=get_port(),
    )
