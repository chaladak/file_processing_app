FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "notifier.py"]

# File: notification_service/requirements.txt
pika==1.3.2
sqlalchemy==2.0.22
psycopg2-binary==2.9.9
requests==2.31.0
