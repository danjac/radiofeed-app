FROM python:3.9.0-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random
ENV DISABLE_COLLECTSTATIC=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /requirements.txt
RUN pip install -r requirements.txt

WORKDIR /app
COPY . /app

RUN useradd -m user
USER user

