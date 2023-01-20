FROM python:3.11.1-buster

WORKDIR /app

COPY requirements.txt ./requirements.txt

COPY nltk.txt ./nltk.txt

RUN pip install --disable-pip-version-check --no-cache-dir -r ./requirements.txt

RUN xargs python -m nltk.downloader <./nltk.txt

COPY . /app
