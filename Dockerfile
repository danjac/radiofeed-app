FROM python:3.9.2-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11 curl ca-certificates

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get install -y nodejs

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -sLO https://github.com/watchexec/watchexec/releases/download/1.14.1/watchexec-1.14.1-x86_64-unknown-linux-gnu.deb \
    && dpkg -i watchexec-1.14.1-x86_64-unknown-linux-gnu.deb \
    && rm -f watchexec-1.14.1-x86_64-unknown-linux-gnu.deb

COPY ./requirements.txt /requirements.txt
RUN pip install -r requirements.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet

WORKDIR /app

COPY postcss.config.js ./postcss.config.js
COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY assets.dockerfile package-lock.json* ./

RUN if [ -d /app/node_modules ]; then rm -Rf /app/node_modules/*; fi

RUN npm cache clean --force
RUN npm install

COPY ./scripts/docker/entrypoint /entrypoint
RUN chmod +x /entrypoint

COPY ./scripts/docker/start-django /start-django
RUN chmod +x /start-django

COPY ./scripts/docker/start-celeryworker /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./scripts/docker/start-celerybeat /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./scripts/docker/start-watchjs /start-watchjs
RUN chmod +x /start-watchjs

COPY ./scripts/docker/start-watchcss /start-watchcss
RUN chmod +x /start-watchcss

ENTRYPOINT ["/entrypoint"]
