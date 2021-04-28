FROM python:3.9.2-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONHASHSEED=random

# dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-11 curl ca-certificates inotify-tools

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get install -y nodejs

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# watchman
RUN curl -sLO https://github.com/facebook/watchman/releases/download/v2021.04.26.00/watchman-v2021.04.26.00-linux.zip \
    && unzip watchman-v2021.04.26.00-linux.zip \
    && mkdir -p /usr/local/var/run/watchman \
    && cd watchman-v2021.04.26.00-linux \
    && cp bin/* /usr/local/bin \
    && cp lib/* /usr/local/lib \
    && chmod 755 /usr/local/bin/watchman \
    && chmod 2777 /usr/local/var/run/watchman

# python requirements
COPY ./requirements.local.txt /requirements.txt
RUN pip install -r requirements.txt

RUN python -m nltk.downloader stopwords
RUN python -m nltk.downloader wordnet

WORKDIR /app

# frontend requirements
COPY postcss.config.js ./postcss.config.js
COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY package-lock.json ./package-lock.json

RUN if [ -d /app/node_modules ]; then rm -Rf /app/node_modules/*; fi

RUN npm cache clean --force
RUN npm install

# scripts
COPY ./scripts/docker/entrypoint /entrypoint
RUN chmod +x /entrypoint

COPY ./scripts/docker/start-webapp /start-webapp
RUN chmod +x /start-webapp

COPY ./scripts/docker/start-celeryworker /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./scripts/docker/start-celerybeat /start-celerybeat
RUN chmod +x /start-celerybeat
