import subprocess, time, os

while True:
    try:
        print("🧠 Launching KRIZZY OPS v3 Enterprise Engine…")
        subprocess.run(["python3", "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Engine crashed: {e}. Restarting in 5s...")
        time.sleep(5)
    except Exception as ex:
        print(f"Unexpected error: {ex}. Rebooting in 10s...")
        time.sleep(10)
