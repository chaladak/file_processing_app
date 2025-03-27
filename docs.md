docker compose up
docker compose ps
docker compose logs
docker compose down
docker compose down -v
docker-compose logs api           # View API service logs
docker-compose logs processor     # View processor service logs
docker-compose logs notifier      # View notification service logs

curl http://localhost:15672


docker compose down && docker compose up --build -d

curl -X POST "http://localhost:8000/upload/" -F "file=@/test.txt"


curl -X POST -F "file=@/path/to/your/file.txt" http://localhost:8000/upload/
curl http://localhost:8000/status/{job_id}

http://localhost:8000/docs#/