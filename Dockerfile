FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8501

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY analytics.py app.py serve.py ./
COPY cur-csv-cursos-da-ufs.csv ./
COPY .streamlit ./.streamlit

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; p=os.environ.get('PORT','8501'); urllib.request.urlopen(f'http://127.0.0.1:{p}/_stcore/health', timeout=4)"]

CMD ["python", "serve.py"]
