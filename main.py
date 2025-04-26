from fastapi import FastAPI
import subprocess
import threading
import os

app = FastAPI()

# Streamlitアプリ起動
def start_streamlit():
    # ローカルではstreamlit run app/streamlit_app.py みたいな形だけど
    # Render上では /app/app/streamlit_app.py というパスになる
    subprocess.Popen(["streamlit", "run", "app/streamlit_app.py", "--server.port=10000", "--server.headless=true"])

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
