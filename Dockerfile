# Install Python dependencies

FROM python:3.12.6-bookworm AS django

ENV PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Python requirements

RUN pip install pdm==2.18.2

COPY ./pyproject.toml ./pdm.lock /app/

RUN pdm install --check --prod --no-editable --no-self --fail-fast

ENV PATH="/app/.venv/bin:$PATH"

# Download NLTK files

COPY ./nltk.txt /app/nltk.txt

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Download Tailwind CLI

COPY . /app

# Compile and collect static files

RUN python manage.py tailwind build && \
    python manage.py collectstatic --no-input
