from fastapi import FastAPI
import subprocess
import threading
import os

app = FastAPI()

# Streamlitアプリ起動
def start_streamlit():
    port = os.environ.get("PORT", "10000")  # Render用に環境変数PORTを拾う
    subprocess.Popen([
        "streamlit", "run", "streamlit_app.py",
        "--server.port", port,
        "--server.headless", "true",
        "--server.address", "0.0.0.0"  # これも必須！！
    ])

# サーバー起動時にStreamlitも一緒に起動する
threading.Thread(target=start_streamlit, daemon=True).start()

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
