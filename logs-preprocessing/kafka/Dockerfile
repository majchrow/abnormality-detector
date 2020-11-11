FROM python:3.8

COPY . /app

WORKDIR /app/

ENV FILEPATH="./resources/data.json"

ENV KAFKA="kafka:9092"

RUN pip install -r requirements.txt

CMD ["python", "producer.py"]