FROM python:3.8

WORKDIR /flask

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY rest rest/

ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_APP=rest/app:create_app

EXPOSE 5000