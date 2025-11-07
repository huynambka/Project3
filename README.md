# IDOR Vulnerability Detection Tool

Automated detection tool for Insecure Direct Object Reference (IDOR) vulnerabilities using AI-powered graph analysis.

## 🚀 Key Features

- **🤖 AI-Powered Analysis**: Google Gemini automatically converts HTTP traffic to structured graph data
- **📦 Batch Processing**: Efficient processing of messages in configurable batches (default: 5)
- **🕸️ Graph Database**: Neo4j-based knowledge graph for relationship analysis
- **🔌 BurpSuite Integration**: Real-time traffic capture and analysis
- **🎯 Modular Architecture**: Extensible design for future IDOR detection algorithms

## Architecture

```
BackServer/
├── src/
│   ├── ai/              # 🤖 Google Gemini integration & batch processor
│   ├── config/          # ⚙️ Configuration and settings (.env support)
│   ├── models/          # 📊 Data models (HTTP messages, graph nodes)
│   ├── parsers/         # 🔍 HTTP request/response parsers
│   ├── graph_db/        # 🗄️ Neo4j client and graph operations
│   ├── server/          # 🌐 Flask server for BurpSuite integration
│   └── utils/           # 🛠️ Utilities (logging, helpers)
├── main.py              # 🎯 Main entry point (3 modes)
├── .env                 # 🔐 Environment variables (API keys, credentials)
├── requirements.txt     # 📦 Python dependencies
└── Dockerfile           # 🐳 Neo4j container setup
```

## Prerequisites

- **Option 1: Docker Compose (Recommended)** 🐳
  - Docker Desktop ([Download](https://www.docker.com/products/docker-desktop))
  - Google Gemini API key ([Get one free](https://makersuite.google.com/app/apikey))
  
- **Option 2: Local Development**
  - Python 3.8+
  - Docker (for Neo4j only)
  - Google Gemini API key
  - BurpSuite (optional, for live traffic analysis)

## 🚀 Quick Start

### Option A: Docker Compose (Recommended) 🐳

**Fastest way to get started - everything in containers!**

#### 1. Configure Environment

Edit `.env` file:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
BATCH_SIZE=5
```

#### 2. Start All Services

```powershell
# Build and start all containers
docker-compose up -d

# View logs
docker-compose logs -f
```

#### 3. Access Services

- **Flask API**: <http://localhost:5000>
- **Neo4j Browser**: <http://localhost:7474>
- **Health Check**: <http://localhost:5000/health>

#### 4. Stop Services

```powershell
docker-compose down
```

**📖 See [DOCKER.md](DOCKER.md) for complete Docker guide**

---

### Option B: Local Development

#### 1. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

#### 2. Start Neo4j Container

```powershell
# Build and run Neo4j
docker build -t neo4j-custom .
docker run -d -p 7474:7474 -p 7687:7687 --name neo4j-container neo4j-custom

# Wait ~10 seconds for Neo4j to start
```

#### 3. Configure Environment Variables

Create or edit `.env` file in the project root:

```env
# Google Gemini API (Get from: https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword

# Batch Processing
BATCH_SIZE=5

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
```

**⚠️ Important**: Get your free Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

#### 4. Start the Server

```powershell
python main.py --mode server
```

Server will start on `http://localhost:5000` 🎉

## 📚 Usage Modes

The tool has **3 operation modes** accessible via `main.py`:

### 1️⃣ Server Mode - Live Traffic Analysis (AI-Powered)

**Best for**: Real-time BurpSuite integration with automatic AI conversion

```powershell
python main.py --mode server
```

**What happens**:
- Flask server listens on `http://localhost:5000`
- BurpSuite extension sends HTTP traffic to `/analyze` endpoint
- Messages are collected in batches (default: 5)
- Each batch is sent to Google Gemini for automatic conversion
- Converted data is loaded into Neo4j graph database

**API Endpoints**:

**POST /analyze** - Submit HTTP traffic from BurpSuite

```json
{
  "request": "GET /api/users/1 HTTP/1.1\r\nAuthorization: Bearer eyJ...\r\n\r\n",
  "response": "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"id\":1,\"username\":\"alice\"}",
  "timestamp": "1762095024427"
}
```

Response (queued):

```json
{
  "status": "queued",
  "message": "Message queued (3/5)",
  "batch_position": 3,
  "batch_size": 5,
  "total_messages": 8
}
```

Response (batch complete):

```json
{
  "status": "batch_complete",
  "message": "Batch of 5 messages sent for processing",
  "batch_position": 5,
  "batch_size": 5
}
```

**GET /status** - Check batch processing status

```powershell
curl http://localhost:5000/status
```

**POST /flush** - Force process incomplete batch (< 5 messages)

```powershell
curl -X POST http://localhost:5000/flush
```

**GET /health** - Health check

```powershell
curl http://localhost:5000/health
```

### 2️⃣ Load Mode - Batch File Processing (Legacy)

**Best for**: Processing saved traffic files (JSONL format)

```powershell
python main.py --mode load --file server_requests.json
```

Loads HTTP traffic from JSON/JSONL files and processes them directly without AI conversion.

### 3️⃣ Present Mode - View Graph Statistics

**Best for**: Viewing current database state

```powershell
python main.py --mode present
```

Output shows:

- Node counts by type
- Sample relationships
- Link to Neo4j Browser

## 🤖 How AI Conversion Works

### Input → Gemini

Batch of 5 raw HTTP messages:

```text
--- Message 1 ---
REQUEST:
POST /api/auth/login HTTP/1.1
Content-Type: application/json
{"username": "alice", "password": "password123"}

RESPONSE:
HTTP/1.1 200 OK
{"token": "eyJ...", "user": {"id": 1, "username": "alice"}}

TIMESTAMP: 1762095024427
---
(4 more messages...)
```

### Gemini Processing ✨

AI automatically:
- ✅ Parses HTTP headers and bodies
- ✅ Extracts endpoint patterns (`/api/users/{id}`)
- ✅ Decodes JWT tokens for user sessions
- ✅ Identifies resources from response bodies
- ✅ Creates proper node relationships
- ✅ Generates unique IDs

### Output → Neo4j

Structured graph data:

```json
{
  "nodes": {
    "endpoints": [{"id": "endpoint_abc", "path": "/api/users/1", "pattern": "/api/users/{id}", "method": "GET"}],
    "requests": [{"id": "request_def", "endpoint_id": "endpoint_abc", "headers": {...}}],
    "responses": [{"id": "response_ghi", "request_id": "request_def", "statusCode": 200}],
    "sessions": [{"id": "session_jkl", "user_id": 1, "username": "alice", "token": "eyJ..."}],
    "resources": [{"id": "resource_mno", "type": "user", "data_id": 1}],
    "parameters": [{"id": "param_pqr", "request_id": "request_def", "type": "path", "key": "id", "value": "1"}]
  }
}
```

## 🗄️ Graph Schema

### Node Types

| Node Type | Description | Key Properties |
|-----------|-------------|----------------|
| **Endpoint** | API endpoints with patterns | `path`, `pattern`, `method` |
| **Request** | HTTP requests | `headers`, `body`, `endpoint_id` |
| **Response** | HTTP responses | `statusCode`, `body`, `request_id` |
| **UserSession** | Auth sessions (JWT tokens) | `user_id`, `username`, `token` |
| **Resource** | Data resources (users, objects) | `type`, `data`, `data_id` |
| **Parameter** | Request parameters | `type`, `key`, `value`, `request_id` |

### Relationships

```text
(Request)-[:TARGETS]->(Endpoint)
(Response)-[:FOR_REQUEST]->(Request)
(Parameter)-[:OF_REQUEST]->(Request)
(UserSession)-[:BELONGS_TO]->(Resource)
```

### Example Graph Pattern (IDOR Detection)

```text
Session A (alice, user_id=1)
    ↓ BELONGS_TO
Resource A (user_id=1)
    ↑ ACCESSES
Request 1 → /api/users/1 → Response (200 OK, user_id=1) ✅ Authorized

Session A (alice, user_id=1)
    ↓ BELONGS_TO
Resource A (user_id=1)
    ↑ ACCESSES
Request 2 → /api/users/2 → Response (200 OK, user_id=2) ⚠️ Potential IDOR!
```

## 🌐 Neo4j Browser Access

Access Neo4j Browser at: <http://localhost:7474>

**Login Credentials**:

- Username: `neo4j`
- Password: `testpassword`

### Useful Cypher Queries

```cypher
// View all nodes
MATCH (n) RETURN n LIMIT 100

// Find all requests to a specific endpoint
MATCH (r:Request)-[:TARGETS]->(e:Endpoint {method: 'GET'})
RETURN r, e

// Find user sessions and their resources
MATCH (s:UserSession)-[:BELONGS_TO]->(res:Resource)
RETURN s, res

// Detect potential IDOR: User accessing different user's resources
MATCH (session:UserSession)-[:BELONGS_TO]->(resource1:Resource),
      (request:Request)-[:TARGETS]->(endpoint:Endpoint),
      (response:Response)-[:FOR_REQUEST]->(request)
WHERE session.user_id <> resource1.data_id
RETURN session, request, response, endpoint
```

## 🔧 Configuration

### Batch Size Tuning

Edit `.env`:

```env
BATCH_SIZE=5   # Default: Process every 5 messages
```

**Options**:

- `BATCH_SIZE=3` → More frequent processing, faster feedback
- `BATCH_SIZE=10` → Less frequent, more efficient Gemini API usage
- `BATCH_SIZE=1` → Real-time processing (expensive)

### Debug Logging

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## 🔌 BurpSuite Extension Configuration

Configure your BurpSuite extension:

```text
Endpoint: http://localhost:5000/analyze
Method: POST
Headers: Content-Type: application/json
Body Format:
{
  "request": "<raw HTTP request>",
  "response": "<raw HTTP response>",
  "timestamp": "<unix timestamp>"
}
```

## 🛠️ Development

### Adding New Node Types

1. Define model in `src/models/graph_models.py`
2. Add extraction logic in `src/ai/gemini_client.py` (update prompt)
3. Add loader method in `src/ai/gemini_graph_loader.py`
4. Update Neo4j client constraints in `src/graph_db/neo4j_client.py`

### Adding IDOR Detection Algorithms

1. Create `src/analyzers/` module
2. Query graph patterns using Neo4j Cypher
3. Implement detection logic (e.g., cross-user access patterns)
4. Generate reports with findings

### Extending Gemini Prompt

Edit `src/ai/gemini_client.py` → `CONVERSION_PROMPT` to:

- Add new node types
- Improve extraction patterns
- Handle new HTTP header formats
- Support additional authentication schemes

## 🐳 Docker Commands

```powershell
# Start existing container
docker start neo4j-container

# Stop container
docker stop neo4j-container

# View logs
docker logs neo4j-container

# Remove container and rebuild
docker rm -f neo4j-container
docker build -t neo4j-custom .
docker run -d -p 7474:7474 -p 7687:7687 --name neo4j-container neo4j-custom

# Reset database (delete all data)
docker exec neo4j-container cypher-shell -u neo4j -p testpassword "MATCH (n) DETACH DELETE n"
```

## 🐛 Troubleshooting

### Neo4j Connection Failed

**Symptoms**: `Failed to connect to Neo4j at bolt://localhost:7687`

**Solutions**:

- Ensure container is running: `docker ps | Select-String "neo4j"`
- Restart container: `docker restart neo4j-container`
- Wait 10-15 seconds after starting for full initialization
- Check credentials match `.env` file

### Gemini API Errors

**Error**: `GEMINI_API_KEY not set, AI conversion will not work`

**Solution**: Add your API key to `.env` file (get from <https://makersuite.google.com/app/apikey>)

**Error**: `429 Rate Limit Exceeded`

**Solutions**:

- Increase `BATCH_SIZE` to reduce API calls
- Wait before sending more batches
- Check [Gemini API quotas](https://ai.google.dev/pricing)

### Batch Not Processing

**Symptoms**: Messages queued but not sent to Gemini

**Solutions**:

- Check status: `curl http://localhost:5000/status`
- Force process incomplete batch: `curl -X POST http://localhost:5000/flush`
- Send more messages to complete the batch (default needs 5)

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solutions**:

- Ensure you're in project root: `cd d:\Code\Project3\BackServer`
- Install dependencies: `pip install -r requirements.txt`
- Check virtual environment is activated

### Flask Server Not Receiving Requests

**Solutions**:

- Test health endpoint: `curl http://localhost:5000/health`
- Check firewall settings (allow port 5000)
- Verify BurpSuite extension sends to correct URL
- Check Flask logs for errors

## 📊 Monitoring & Logs

### Watch Real-Time Processing

```powershell
python main.py --mode server
```

**Example output**:

```text
2025-11-03 15:00:01 - INFO - Message added to batch: 1/5
2025-11-03 15:00:02 - INFO - Message added to batch: 2/5
2025-11-03 15:00:03 - INFO - Message added to batch: 3/5
2025-11-03 15:00:04 - INFO - Message added to batch: 4/5
2025-11-03 15:00:05 - INFO - Message added to batch: 5/5
2025-11-03 15:00:05 - INFO - Batch complete, processing...
2025-11-03 15:00:05 - INFO - Sending batch to Gemini...
2025-11-03 15:00:07 - INFO - Successfully converted batch
2025-11-03 15:00:07 - INFO - Loading into Neo4j...
2025-11-03 15:00:08 - INFO - Graph data loaded ✅
```

## 🎯 Advantages of AI-Powered Batch Processing

| Feature | Benefit |
|---------|---------|
| 🤖 **AI Conversion** | No manual parsing rules needed |
| 📦 **Batch Processing** | Reduced API costs (5x fewer calls) |
| 🧠 **Context Awareness** | Gemini sees related requests together |
| 🔍 **Pattern Recognition** | Better endpoint pattern extraction |
| 🎯 **Smart Grouping** | Session-aware processing |
| ⚡ **Async Processing** | Non-blocking, continues receiving traffic |

## 🚀 Next Steps & Future Enhancements

### Immediate Actions

1. ✅ Add your Gemini API key to `.env`
2. ✅ Configure BurpSuite extension
3. ✅ Send test traffic
4. ✅ View results in Neo4j Browser

### Future Development Roadmap

- [ ] **IDOR Detection Algorithms** - Automated vulnerability identification
- [ ] **Pattern Matching** - Access control anomaly detection
- [ ] **Report Generation** - PDF/HTML vulnerability reports
- [ ] **Web UI Dashboard** - Interactive visualization
- [ ] **Machine Learning** - Anomaly detection from graph patterns
- [ ] **Protocol Support** - GraphQL, gRPC, WebSocket
- [ ] **Rate Limiting** - Smart throttling for Gemini API
- [ ] **Export/Import** - Share analysis results

## 📄 Additional Documentation

- **AI_BATCH_PROCESSING.md** - Detailed AI integration guide
- **Dockerfile** - Neo4j container configuration
- **.env.example** - Environment template

## 📝 License

This project is for security research and educational purposes.

---

**Made with ❤️ for Bug Bounty Hunters and Security Researchers**
