from __future__ import annotations

import os
import subprocess
import time

from discord_utils import post_err, post_ops
from kpi import kpi_push


def run_process_guard() -> None:
    while True:
        try:
            post_ops("Launching KRIZZY OPS engine")
            kpi_push("boot", {"guard": True})
            subprocess.run(["python", "main.py"], check=True)
        except subprocess.CalledProcessError as e:
            post_err(f"Engine crashed: {e}")
            time.sleep(5)
        except Exception as ex:  # noqa: BLE001
            post_err(f"Unexpected error: {ex}")
            time.sleep(10)


if __name__ == "__main__":
    run_process_guard()
