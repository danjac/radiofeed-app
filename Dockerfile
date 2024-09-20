# Install Python dependencies

FROM python:3.12.6-bookworm AS python-base

ENV LC_CTYPE=C.utf8 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

RUN pip install pdm==2.18.2

COPY ./pyproject.toml ./pdm.lock /app/

RUN pdm install --check --prod --no-editable --no-self --fail-fast

ENV PATH="/app/.venv/bin:$PATH"

# Download NLTK files

FROM python-base AS nltk-corpora

COPY ./nltk.txt /app/

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < /app/nltk.txt

# Build static assets

FROM python-base AS staticfiles

COPY . /app

RUN python manage.py tailwind build && \
    python manage.py collectstatic --no-input

FROM python-base AS webapp

COPY --from=nltk-corpora /root/nltk_data /root/nltk_data
COPY --from=staticfiles /app/staticfiles /app/staticfiles

COPY . /app
