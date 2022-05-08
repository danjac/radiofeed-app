FROM node:18-buster AS node

WORKDIR /app

COPY ./package.json ./package.json
COPY ./package-lock.json ./package-lock.json

RUN npm cache clean --force && npm ci

FROM python:3.10.4-buster AS django

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r ./requirements.txt

COPY ./nltk.txt ./nltk.txt

RUN xargs python -m nltk.downloader <./nltk.txt

COPY . .
