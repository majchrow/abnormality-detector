FROM python:3.8-slim-buster

WORKDIR /test-producer

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV BRIDGE_USERNAME=username
ENV BRIDGE_PASSWORD=password
EXPOSE 445
