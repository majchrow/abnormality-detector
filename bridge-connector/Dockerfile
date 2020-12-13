FROM python:3.8

WORKDIR /bridge-connector

COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src src/
RUN pip install -e .

ENV BRIDGE_USERNAME=username
ENV BRIDGE_PASSWORD=password

