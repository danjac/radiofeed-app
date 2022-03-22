FROM nikolaik/python-nodejs:python3.10-nodejs17-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-13

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet
RUN python -m nltk.downloader omw-1.4

COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY package-lock.json ./package-lock.json

RUN npm cache clean --force && npm ci
