# src/tools/tests_runner.py
import subprocess

def run_tests():
    proc = subprocess.run(
        ["pytest", "--disable-warnings", "--maxfail=1"],
        capture_output=True,
        text=True
    )
    return proc.returncode, proc.stdout + proc.stderr
