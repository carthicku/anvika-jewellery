# Production image for the FastAPI backend (docs/operations/DEPLOYMENT.md).
# Build:  docker build -t store-backend:<git-sha> backend
# Migrate: docker run --rm --env-file /opt/store/backend.env store-backend:<git-sha> python -m alembic upgrade head
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first (cached layer). Versions are pinned in requirements.txt.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Never run as root. var/ holds local media/mail only when those backends are used.
RUN useradd --system --uid 10001 --home-dir /app store \
    && mkdir -p /app/var \
    && chown -R store:store /app/var
USER store

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"

# Two workers fit a small VM; background jobs use SKIP LOCKED so both may run them safely.
# Client IPs come from X-Forwarded-For through the app's own TRUSTED_PROXY_COUNT=1 (Caddy is the
# only proxy), so uvicorn's proxy-header rewriting stays at its safe default.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", \
     "--no-server-header"]
