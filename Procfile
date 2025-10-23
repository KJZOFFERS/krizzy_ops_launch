web: gunicorn main:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT
watchdog: python process_guard.py
