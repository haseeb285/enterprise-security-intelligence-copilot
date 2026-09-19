FROM python:3.11.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    HOME=/home/esic

RUN groupadd --gid 10001 esic \
    && useradd --uid 10001 --gid esic --create-home --shell /usr/sbin/nologin esic

WORKDIR /app
COPY requirements-container.constraints requirements-frontend.txt ./
RUN python -m pip install --no-cache-dir \
    --constraint requirements-container.constraints \
    --requirement requirements-frontend.txt
COPY frontend ./frontend
COPY .streamlit ./.streamlit
RUN chown -R esic:esic /app /home/esic

USER 10001:10001
EXPOSE 8501
CMD ["streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
