# Dockerfile for Neo4j graph database
# Usage:
#   docker build -t neo4j-custom .
#   docker run -d -p 7474:7474 -p 7687:7687 --name neo4j-container neo4j-custom

FROM neo4j:5.15.0

# Set environment variables for initial password and config
ENV NEO4J_AUTH=neo4j/testpassword

# Expose HTTP (7474) and Bolt (7687) ports
EXPOSE 7474 7687

# Optional: configure additional settings
ENV NEO4J_dbms_memory_pagecache_size=512M
ENV NEO4J_dbms_memory_heap_initial__size=512M
ENV NEO4J_dbms_memory_heap_max__size=1G

# Default command starts Neo4j
CMD ["neo4j"]
