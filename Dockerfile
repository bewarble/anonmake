FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system anonmake \
    && useradd --system --gid anonmake --home-dir /app anonmake

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

RUN chmod +x /app/docker-entrypoint.sh \
    && chown -R anonmake:anonmake /app

USER anonmake

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "app.main"]
