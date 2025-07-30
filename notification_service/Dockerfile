FROM python:3.9-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tests/requirements.txt /app/tests/requirements.txt
RUN pip install -r /app/tests/requirements.txt

COPY . .

CMD ["python", "notifier.py"]
