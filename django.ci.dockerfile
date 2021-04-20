FROM python:3.9.2-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./poetry.lock /poetry.lock
COPY ./pyproject.toml /pyproject.toml

RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet

WORKDIR /app
