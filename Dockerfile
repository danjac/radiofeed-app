FROM python:3.10.1-buster AS django

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11

WORKDIR /app

COPY ./requirements.txt ./requirements.txt
COPY ./dev-requirements.txt ./dev-requirements.txt

RUN pip install -r ./requirements.txt -r ./dev-requirements.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet
RUN python -m nltk.downloader omw-1.4

# scripts
COPY ./docker/start-webapp /start-webapp
RUN chmod +x /start-webapp

COPY ./docker/start-worker /start-worker
RUN chmod +x /start-worker

COPY ./docker/start-tailwind /start-tailwind
RUN chmod +x /start-tailwind
