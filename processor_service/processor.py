import os
import json
import time
import pika
import boto3
import logging
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy.orm import declarative_base

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the same models to match the API service
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

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# S3 setup
s3_client = boto3.client(
    's3',
    endpoint_url=os.environ.get("S3_ENDPOINT"),
    aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
    region_name='us-east-1'
)
BUCKET_NAME = "file-processing"

# NFS path
NFS_PATH = os.environ.get("NFS_MOUNT_PATH")

# RabbitMQ setup
def get_rabbitmq_connection():
    """Create and return a persistent RabbitMQ connection."""
    global rabbitmq_connection
    if 'rabbitmq_connection' not in globals() or rabbitmq_connection.is_closed:
        logger.info("Establishing new RabbitMQ connection...")
        params = pika.URLParameters(os.environ.get("RABBITMQ_URL") + "?heartbeat=600")
        rabbitmq_connection = pika.BlockingConnection(params)
    return rabbitmq_connection

def process_file(nfs_path, job_id):
    """
    Process file and send result to RabbitMQ
    """
    logger.info(f"Processing file at {nfs_path}")
    
    # Check if the file exists on NFS path
    if not os.path.exists(nfs_path):
        logger.error(f"File not found: {nfs_path}")
        return  # Early exit if file doesn't exist
    
    # Simulate processing time
    time.sleep(5)
    
    # Processing result
    result = {
        "size_bytes": os.path.getsize(nfs_path),
        "processed_timestamp": datetime.now().isoformat(),
        "success": True
    }
    
    # Update database
    try:
        db = SessionLocal()
        file_record = db.query(FileRecord).filter(FileRecord.id == job_id).first()
        if file_record:
            file_record.status = "processed"
            file_record.processed_at = datetime.now()
            file_record.processing_result = json.dumps(result)
            db.commit()
            logger.info(f"Database updated: File {job_id} processed")
        db.close()
    except Exception as e:
        logger.error(f"Error updating database for job {job_id}: {str(e)}")
        return  # Skip further processing if DB update fails
    
    # Reuse RabbitMQ connection
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue='notifications', durable=True)  # Ensure queue exists
        
        notification = {
            "job_id": job_id,
            "status": "processed",
            "result": result
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='notifications',
            body=json.dumps(notification)
        )
        connection.close()
        logger.info(f"Notification sent for job {job_id}")
    except Exception as e:
        logger.error(f"Error sending notification for job {job_id}: {str(e)}")

def callback(ch, method, properties, body):
    message = json.loads(body)
    job_id = message["job_id"]
    nfs_path = message["nfs_path"]
    
    logger.info(f"Received processing job for {job_id}")
    
    try:
        process_file(nfs_path, job_id)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing file {job_id}: {str(e)}")
        # In case of error, update status and notify
        try:
            db = SessionLocal()
            file_record = db.query(FileRecord).filter(FileRecord.id == job_id).first()
            if file_record:
                file_record.status = "error"
                file_record.processing_result = json.dumps({"error": str(e)})
                db.commit()
            db.close()
            
            # Send error notification
            error_connection = get_rabbitmq_connection()
            error_channel = error_connection.channel()
            error_channel.queue_declare(queue='notifications')
            
            notification = {
                "job_id": job_id,
                "status": "error",
                "result": {"error": str(e)}
            }
            
            error_channel.basic_publish(
                exchange='',
                routing_key='notifications',
                body=json.dumps(notification)
            )
            error_connection.close()
            logger.info(f"Error notification sent for job {job_id}")
        except Exception as inner_e:
            logger.error(f"Error handling failure for {job_id}: {str(inner_e)}")
        
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    logger.info("File processor service starting...")
    
    # Wait for RabbitMQ to be ready
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare the queue
    channel.queue_declare(queue='file_processing')
    
    # Set prefetch count to limit the number of unacknowledged messages
    channel.basic_qos(prefetch_count=1)
    
    # Register the callback
    channel.basic_consume(
        queue='file_processing',
        on_message_callback=callback
    )
    
    logger.info("Waiting for file processing jobs. To exit press CTRL+C")
    
    # Start consuming
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Stopping consumer...")
        channel.stop_consuming()
    
    # Close the connection
    connection.close()
    logger.info("Consumer stopped")

if __name__ == "__main__":
    main()
