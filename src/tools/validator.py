# src/tools/validator.py
import ast

ALLOWED_EXTENSIONS = {".py", ".json", ".txt", ".md", ".yml", ".yaml"}


def validate_path(path):
    if ".." in path or path.startswith("/"):
        raise ValueError("Invalid path traversal.")
    if not any(path.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("File extension not allowed.")
    return True


def validate_python(content):
    try:
        ast.parse(content)
    except SyntaxError as e:
        raise ValueError(f"Invalid Python syntax: {e}")
    return True
