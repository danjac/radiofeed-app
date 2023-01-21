FROM python:3.11.1-buster

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install -r /app/requirements.txt --no-cache-dir

COPY ./nltk.txt /app/nltk.txt

RUN xargs python -m nltk.downloader < /app/nltk.txt

COPY . /app

CMD ["./release.sh"]
