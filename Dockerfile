FROM python:3.11.1-buster

ENV PYTHONUNBUFFERED=1

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY ./requirements/prod.txt /app/requirements/prod.txt

RUN pip install -r /app/requirements/prod.txt --no-cache-dir

COPY ./nltk.txt /app/nltk.txt

RUN xargs python -m nltk.downloader < /app/nltk.txt

COPY . /app

RUN python manage.py collectstatic --no-input --traceback --settings=radiofeed.settings.production

CMD ["./deploy.sh"]
