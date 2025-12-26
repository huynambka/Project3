docker stop idor-app idor-neo4j
docker rm idor-app idor-neo4j

docker volume rm project3-idor_neo4j_data project3-idor_neo4j_logs

docker compose up -d --build