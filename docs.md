### Set up app
docker compose build processor
docker compose up
docker compose down -v
(or)
docker compose down && docker compose up --build -d

### Check logs or some services
docker-compose logs processor     # View processor service logs

### Check RabbitMQ service \ manage service
curl http://localhost:15672

### Upload file from drive
curl -X POST "http://localhost:8000/upload/" -F "file=@/test.txt"

### Check job status
curl http://localhost:8000/status/{job_id}

### API docs
http://localhost:8000/docs#/

### API health
http://localhost:8000/health

### Minio console
http://localhost:9001/

### Check database records
docker exec -it file_processing_app-postgres-1 psql -U admin -d fileprocessing
\dt
SELECT * FROM file_records LIMIT 40;
SELECT * FROM notifications LIMIT 40;
\q
