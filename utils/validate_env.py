import os, sys

def validate_env(keys):
    for k in keys:
        if not os.getenv(k):
            sys.exit(f"Missing environment variable: {k}")
