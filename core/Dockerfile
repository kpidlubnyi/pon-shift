FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    netcat-openbsd \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock* ./

RUN uv pip install --no-cache -r pyproject.toml

COPY ./core .

RUN python3 manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT [ "./entrypoint.sh" ]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "core.wsgi:application"]
