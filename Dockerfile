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

# Python requirements

RUN pip install pdm==2.18.2

COPY ./pyproject.toml ./pdm.lock /app/

RUN pdm install --check --prod --no-editable --no-self --fail-fast

ENV PATH="/app/.venv/bin:$PATH"

FROM python-base AS deployment-assets

# Download NLTK files

COPY ./nltk.txt /app/

COPY ./scripts /app/scripts

RUN /app/scripts/download-nltk.sh /app/nltk.txt

COPY . /app

# Build static assets

RUN /app/scripts/build-assets.sh


FROM python-base AS webapp

COPY --from=deployment-assets /app/staticfiles /app/staticfiles
COPY --from=deployment-assets /root/nltk_data /root/nltk_data

COPY . /app
