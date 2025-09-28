from fastapi import FastAPI
import subprocess
import threading
import os

app = FastAPI()

# /run_notify にアクセスされたらLINE通知する
@app.get("/run_notify")
def run_notify():
    try:
        # notify_auto.pyを直接実行する！
        result = subprocess.run(
            ["python3", "-u", "notify_auto.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {
            "status": "ok",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
