import os
import time


def scheduler_loop():
    while True:
        # DB interactions removed to keep scheduler DB-free by default
        time.sleep(60)
