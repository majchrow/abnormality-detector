FROM python:3.8

WORKDIR /aiohttp

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

EXPOSE 5000