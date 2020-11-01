FROM python:3.8

WORKDIR /flask

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_APP=src/app.py

EXPOSE 5000