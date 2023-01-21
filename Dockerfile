FROM python:3.11.1-buster

ENV PYTHONUNBUFFERED=1

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt --no-cache-dir

COPY ./nltk.txt /app/nltk.txt

RUN xargs python -m nltk.downloader < /app/nltk.txt

COPY ./static /app/static

RUN python manage.py collectstatic --settings=radiofeed.settings.production --no-input

COPY . /app

CMD ["./deploy.sh"]
