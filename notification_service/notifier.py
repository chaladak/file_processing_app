import os
import json
import time
import pika
import logging
import requests
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the same models to match other services
Base = declarative_base()

class FileRecord(Base):
    __tablename__ = "file_records"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    s3_path = Column(String, nullable=False)
    nfs_path = Column(String, nullable=False)
    status = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    processing_result = Column(Text, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False)
    details = Column(Text, nullable=True)

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# RabbitMQ setup
def get_rabbitmq_connection():
    retry_count = 0
    max_retries = 30
    while retry_count < max_retries:
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(os.environ.get("RABBITMQ_URL"))
            )
            return connection
        except pika.exceptions.AMQPConnectionError:
            retry_count += 1
            logger.info(f"Connection attempt {retry_count}/{max_retries} failed. Retrying...")
            time.sleep(2)
    
    raise Exception("Failed to connect to RabbitMQ after multiple attempts")

def send_notification(job_id, status, result):
    """
    Send notification about file processing results
    In a real application, this would send emails, push notifications, etc.
    """
    logger.info(f"Sending notification for job {job_id} with status {status}")
    
    # In a real application, you would send notifications via email, SMS, webhook, etc.
    # For this example, we'll just log the notification and save it to the database
    
    # Simulate HTTP webhook call (for demonstration purposes)
    try:
        # This is a placeholder and would typically call a real webhook endpoint
        # webhook_url = "https://example.com/webhook"
        # response = requests.post(webhook_url, json={
        #     "job_id": job_id,
        #     "status": status,
        #     "result": result
        # })
        # logger.info(f"Webhook response: {response.status_code}")
        
        # Instead, we'll just log the notification
        logger.info(f"NOTIFICATION: Job {job_id} - Status: {status} - Result: {result}")
        
        # Save notification to database
        db = SessionLocal()
        notification = Notification(
            id=f"{job_id}_{datetime.now().timestamp()}",
            job_id=job_id,
            status=status,
            sent_at=datetime.now(),
            details=json.dumps(result)
        )
        db.add(notification)
        db.commit()
        db.close()
        
        return True
    except Exception as e:
        logger.error(f"Error sending notification for job {job_id}: {str(e)}")
        return False

def callback(ch, method, properties, body):
    message = json.loads(body)
    job_id = message["job_id"]
    status = message["status"]
    result = message.get("result", {})
    
    logger.info(f"Received notification job for {job_id} with status {status}")
    
    try:
        send_notification(job_id, status, result)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing notification for job {job_id}: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    logger.info("Notification service starting...")
    
    # Wait for RabbitMQ to be ready
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare the queue
    channel.queue_declare(queue='notifications')
    
    # Set prefetch count to limit the number of unacknowledged messages
    channel.basic_qos(prefetch_count=1)
    
    # Register the callback
    channel.basic_consume(queue='notifications', on_message_callback=callback)
    
    logger.info("Waiting for notification messages. To exit press CTRL+C")
    channel.start_consuming()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Notification service stopping...")