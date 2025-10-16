import time
from rei_dispo_engine import run_rei_dispo
from govcon_subtrap_engine import run_govcon_subtrap

if __name__ == "__main__":
    while True:
        try:
            print("KRIZZY OPS LOOP ACTIVE")
            run_rei_dispo()
            run_govcon_subtrap()
        except Exception as e:
            print("Error:", e)
        time.sleep(300)  # waits 5 minutes before next cycle

