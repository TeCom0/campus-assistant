FROM python:3.12-slim

# No .pyc files in the image, and log output reaches `docker logs` right away
# instead of sitting in a buffer. HF_HOME: where the embedding model is
# stored, outside any user's home so the non-root user below can read it.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface

WORKDIR /app/backend

# Slowest-changing layers first. Docker reuses a cached layer until a file it
# copied changes, so editing app/ code doesn't reinstall torch.

# CPU-only torch: the default Linux build bundles CUDA (several GB).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Only the dependency list from pyproject.toml, not the package itself:
# installing the package would need app/ copied in first, so every code
# change would invalidate this layer.
COPY pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

# Download the embedding model at build time, so a container starts without
# network access and every container uses the same model files. Must match
# EMBEDDING_MODEL_NAME in app/config.py; HF_HUB_OFFLINE makes a mismatch fail
# loudly at the first search instead of downloading at runtime.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
ENV HF_HUB_OFFLINE=1

COPY app ./app

# Don't run the server as root: if it's ever compromised, the attacker gets a
# user that can't modify the image's files.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# 0.0.0.0, not 127.0.0.1: inside a container, localhost is only reachable from
# within that container, so the port mapping couldn't reach the server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
