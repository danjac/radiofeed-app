FROM python:3.11.1-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt ./requirements.txt

COPY nltk.txt ./nltk.txt

RUN pip install -r ./requirements.txt

RUN xargs python -m nltk.downloader <./nltk.txt

COPY . /app
