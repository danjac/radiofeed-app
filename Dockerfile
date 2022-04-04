FROM python:3.10.3-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

ENV NODE_VERSION 17.8.0

RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove

RUN curl "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz" -O \
    && tar -xf "node-v$NODE_VERSION-linux-x64.tar.xz" \
    && ln -s "/node-v$NODE_VERSION-linux-x64/bin/node" /usr/local/bin/node \
    && ln -s "/node-v$NODE_VERSION-linux-x64/bin/npm" /usr/local/bin/npm \
    && ln -s "/node-v$NODE_VERSION-linux-x64/bin/npx" /usr/local/bin/npx \
    && rm -f "/node-v$NODE_VERSION-linux-x64.tar.xz"

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet
RUN python -m nltk.downloader omw-1.4

COPY package.json ./package.json
COPY package-lock.json ./package-lock.json

RUN npm cache clean --force && npm ci
