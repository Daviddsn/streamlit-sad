"""Sobe o Streamlit na porta que o EasyPanel informar."""

import os

port = os.environ.get("PORT", "8501")
os.execvp(
    "streamlit",
    [
        "streamlit",
        "run",
        "app.py",
        "--server.port",
        port,
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
        "--server.enableWebsocketCompression",
        "false",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ],
)
