FROM python:3.11.1-buster

ENV PYTHONUNBUFFERED=1

ENV PYTHONDONTWRITEBYTECODE=1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt --no-cache-dir

COPY ./nltk.txt /app/nltk.txt

RUN cat nltk.txt | xargs -I{} python -c "import nltk; nltk.download('{}')"

COPY . /app

RUN python manage.py collectstatic --no-input --traceback --settings=radiofeed.settings.production

CMD ["./deploy.sh"]
