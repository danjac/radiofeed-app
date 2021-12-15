FROM python:3.10.1-buster AS backend

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet

# scripts

COPY ./docker/start-webapp /start-webapp
RUN chmod +x /start-webapp

COPY ./docker/start-worker /start-worker
RUN chmod +x /start-worker

# frontend

FROM node:17-buster AS frontend

WORKDIR /app

COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY package-lock.json ./package-lock.json

RUN npm cache clean --force
RUN npm ci
