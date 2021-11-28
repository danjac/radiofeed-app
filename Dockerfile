FROM python:3.10.0-buster


ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

# dependencies

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# python requirements

RUN pip install poetry

COPY ./requirements-dev.txt ./requirements-dev.txt

RUN pip install -r ./requirements-dev.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet

# frontend requirements

COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY package-lock.json ./package-lock.json

RUN npm cache clean --force
RUN npm ci


# scripts

COPY ./docker/start-webapp /start-webapp
RUN chmod +x /start-webapp

COPY ./docker/start-worker /start-worker
RUN chmod +x /start-worker
