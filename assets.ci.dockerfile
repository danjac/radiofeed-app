FROM node:14.13.1-buster-slim

WORKDIR /app

COPY postcss.config.js ./postcss.config.js
COPY tailwind.config.js ./tailwind.config.js
COPY package.json ./package.json
COPY assets.ci.dockerfile package-lock.json* ./

RUN if [ -d /app/node_modules ]; then rm -Rf /app/node_modules/*; fi

RUN npm cache clean --force
RUN npm install
