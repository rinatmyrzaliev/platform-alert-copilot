FROM python:latest

WORKDIR /app

RUN apt-get update
RUN apt-get install -y curl wget

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD uvicorn src.main:app --host 0.0.0.0 --port 8080