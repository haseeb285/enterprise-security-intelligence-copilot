FROM python:3.11.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/esic/.cache/huggingface \
    HOME=/home/esic

RUN groupadd --gid 10001 esic \
    && useradd --uid 10001 --gid esic --create-home --shell /usr/sbin/nologin esic

WORKDIR /app
COPY requirements-container.constraints requirements-api.txt ./
RUN python -m pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.14.0 \
    && python -m pip install --no-cache-dir \
    --constraint requirements-container.constraints \
    --requirement requirements-api.txt

COPY app ./app
COPY migrations ./migrations
COPY data/policies/synthetic ./data/policies/synthetic
COPY alembic.ini ./
COPY docker/api-entrypoint.sh /usr/local/bin/esic-api-entrypoint
RUN chmod 0555 /usr/local/bin/esic-api-entrypoint \
    && mkdir -p /app/models /app/work /app/data/runtime /home/esic/.cache/huggingface \
    && chown -R esic:esic /app /home/esic

USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/esic-api-entrypoint"]
CMD ["uvicorn", "app.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS trainer
USER root
COPY requirements-trainer.txt ./
RUN python -m pip install --no-cache-dir \
    --constraint requirements-container.constraints \
    --requirement requirements-trainer.txt
USER 10001:10001
