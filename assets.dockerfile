FROM node:14.13.1-buster-slim

WORKDIR /app

COPY postcss.config.js ./postcss.config.js
COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY yarn.lock ./yarn.lock

RUN yarn

