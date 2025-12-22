docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

docker system prune -af
docker volume prune -f

docker compose up -d --build

docker compose -f example-app/docker-compose.yml up -d --build