# Production Dockerfile for application

FROM node:20-buster AS assets

WORKDIR /app

COPY ./package.json /app/package.json

COPY ./package-lock.json /app/package-lock.json

RUN npm install

COPY . /app

ENV NODE_ENV=production

RUN npm run build

FROM python:3.11.4-buster AS app

ENV PYTHONUNBUFFERED=1

ENV PYTHONDONTWRITEBYTECODE=1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt --no-cache-dir

COPY ./nltk.txt /app/nltk.txt

RUN xargs -I{} python -c "import nltk; nltk.download('{}')" < nltk.txt

COPY . /app

COPY --from=assets /app/static /app/static

RUN python manage.py collectstatic --no-input --traceback
