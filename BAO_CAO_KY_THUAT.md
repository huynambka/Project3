# BÁO CÁO KỸ THUẬT
## HỆ THỐNG PHÁT HIỆN LỖ HỔNG IDOR SỬ DỤNG GRAPH DATABASE

---

**Sinh viên thực hiện:** Nguyễn Huy Nam
**MSSV:** 20225367  
**Lớp:** IT2-03
**Giảng viên hướng dẫn:** Ngô Quỳnh Thu  

**Thời gian thực hiện:** Tháng 12/2025

---

## MỤC LỤC

1. [CƠ SỞ LÝ THUYẾT](#1-cơ-sở-lý-thuyết)
2. [KIẾN TRÚC HỆ THỐNG](#2-kiến-trúc-hệ-thống)
3. [SƠ ĐỒ VÀ CÁCH HOẠT ĐỘNG](#3-sơ-đồ-và-cách-hoạt-động)
4. [HƯỚNG PHÁT TRIỂN TIẾP THEO](#4-hướng-phát-triển-tiếp-theo)
5. [KẾT LUẬN](#5-kết-luận)
6. [TÀI LIỆU THAM KHẢO](#6-tài-liệu-tham-khảo)

---

## 1. CƠ SỞ LÝ THUYẾT

### 1.1. Lỗ hổng IDOR (Insecure Direct Object Reference)

**Định nghĩa:**  
IDOR là lỗ hổng bảo mật xảy ra khi ứng dụng web cho phép người dùng truy cập trực tiếp vào các đối tượng (object) thông qua tham số có thể đoán được (như ID), mà không có kiểm tra quyền truy cập đầy đủ.

**Ví dụ:**
```
GET /api/users/123  → User A có thể xem thông tin của mình
GET /api/users/456  → User A thay đổi ID → xem được thông tin User B (IDOR!)
```

**Đặc điểm:**
- Nằm trong OWASP Top 10 (A01:2021 - Broken Access Control)
- Nguy hiểm: Cao - Có thể dẫn đến rò rỉ dữ liệu, leo thang đặc quyền
- Phổ biến: Rất cao - Xuất hiện trong hầu hết các ứng dụng web

### 1.2. Graph Database

**Định nghĩa:**  
Graph database là hệ quản trị cơ sở dữ liệu sử dụng cấu trúc đồ thị (graph) với các nút (nodes), cạnh (edges/relationships) và thuộc tính để biểu diễn và lưu trữ dữ liệu.

**Neo4j:**  
Neo4j là graph database phổ biến nhất, sử dụng ngôn ngữ truy vấn Cypher.

**Ưu điểm cho phân tích bảo mật:**
- **Biểu diễn tự nhiên**: Quan hệ giữa User-Request-Resource
- **Truy vấn phức tạp**: Dễ dàng tìm pattern (VD: 2 users truy cập cùng resource)
- **Hiệu suất cao**: Tối ưu cho truy vấn quan hệ đa tầng
- **Trực quan hóa**: Dễ dàng visualize attack patterns

### 1.3. Rule-Based Parsing

**Khái niệm:**  
Phân tích HTTP requests dựa trên các quy tắc (rules) được định nghĩa trước trong file YAML, thay vì sử dụng AI/Machine Learning.

**Ưu điểm:**
- ✅ Deterministic - Kết quả nhất quán, có thể dự đoán
- ✅ Không phụ thuộc external AI services
- ✅ Nhanh - Xử lý real-time
- ✅ Dễ tùy chỉnh - Chỉnh sửa rules trong YAML
- ✅ Transparent - Dễ debug và audit

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                         IDOR DETECTION SYSTEM                    │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   BurpSuite  │          │    Flask     │          │    Neo4j     │
│   Extension  │ ────────>│   Server     │ ────────>│   Database   │
│              │   HTTP    │              │   Bolt   │              │
│  (Traffic    │          │  (Parser +   │          │  (Graph      │
│   Capture)   │          │   Loader)    │          │   Storage)   │
└──────────────┘          └──────────────┘          └──────────────┘
       │                         │                         │
       │                         │                         │
       v                         v                         v
   Intercept              Real-time process           Store as graph
   HTTP traffic           & extract entities          for analysis
```

### 2.2. Các thành phần chính

#### 2.2.1. Docker Infrastructure

**docker-compose.yml** định nghĩa 2 services:

```yaml
services:
  neo4j:
    - Ports: 7474 (HTTP), 7687 (Bolt)
    - Database: Neo4j 5.15.0
    - Memory: 512M-1G
    
  app:
    - Port: 5000
    - Framework: Flask (Python 3.11)
    - Dependencies: Neo4j, PyYAML, requests
```

#### 2.2.2. Flask Application Layer

**Endpoints:**

| Endpoint | Method | Mô tả |
|----------|---------|-------|
| `/health` | GET | Health check |
| `/analyze` | POST | Nhận và phân tích HTTP requests |
| `/statistics` | GET | Thống kê graph database |
| `/config` | GET | Xem cấu hình parser |

#### 2.2.3. Rule-Based Parser

**File:** `src/parsers/yaml_rule_parser.py`

**Chức năng:**
- Parse HTTP requests thành graph nodes/relationships
- Sử dụng regex patterns từ `parsing_rules.yaml`
- Extract: User, Resource, Parameters, Headers, Body, Endpoint

**Quy trình parsing:**
```python
HTTPRequest → YAMLRuleBasedParser → Graph Components
                                          ├── Nodes (User, Resource, Request, etc.)
                                          └── Relationships (AUTHENTICATED_AS, ACCESSES, etc.)
```

#### 2.2.4. Graph Database Layer

**File:** `src/graph_db/rule_based_loader.py`

**Chức năng:**
- Nhận graph components từ parser
- Tạo/cập nhật nodes trong Neo4j
- Tạo relationships
- Track temporal ordering (FOLLOWS)

### 2.3. YAML Configuration

**File:** `config/parsing_rules.yaml`

**Nội dung chính:**

```yaml
# 1. Parameter classification
parameter_patterns:
  ID, USER, RESOURCE, FILE, ACCOUNT, ORDER, SESSION, etc.

# 2. User extraction
user_extraction:
  jwt: JWT token decoding
  cookie: Cookie parsing patterns

# 3. Resource extraction  
resource_extraction:
  url_patterns: /api/users/{id}
  parameter_patterns: userId, orderId, etc.

# 4. Node templates
node_templates:
  Request, Parameter, Header, Body, Endpoint, User, Resource

# 5. Relationship types
relationship_types:
  HAS_PARAMETER, HAS_HEADER, TARGETS, AUTHENTICATED_AS, 
  ACCESSES, FOLLOWS, OWNS
```

---

## 3. SƠ ĐỒ VÀ CÁCH HOẠT ĐỘNG

### 3.1. Luồng dữ liệu tổng quan

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1: TRAFFIC CAPTURE                                           │
└─────────────────────────────────────────────────────────────────────┘

BurpSuite intercepts HTTP traffic:
┌──────────────────────────────────────┐
│ GET /api/users/123 HTTP/1.1          │
│ Host: example.com                     │
│ Authorization: Bearer eyJhbGc...     │
│ Cookie: session=abc123                │
└──────────────────────────────────────┘
              │
              v
        Send to Flask /analyze endpoint


┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2: PARSING & EXTRACTION                                      │
└─────────────────────────────────────────────────────────────────────┘

YAMLRuleBasedParser processes request:

1. Extract User from JWT/Cookie
   └──> User(user_id="5", username="alice", auth_method="jwt")

2. Extract Resource from URL pattern
   └──> Resource(resource_id="123", resource_type="user", operation="read")

3. Create Request node
   └──> Request(method="GET", url="/api/users/123", timestamp="...")

4. Extract Parameters, Headers, Body, Endpoint
   └──> Parameter, Header, Body, Endpoint nodes

5. Create Relationships
   ├──> Request -[:AUTHENTICATED_AS]-> User
   ├──> Request -[:ACCESSES]-> Resource
   ├──> Request -[:TARGETS]-> Endpoint
   ├──> Request -[:HAS_PARAMETER]-> Parameter
   └──> Request -[:FOLLOWS]-> PreviousRequest (if same user)


┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 3: GRAPH STORAGE                                             │
└─────────────────────────────────────────────────────────────────────┘

RuleBasedGraphLoader writes to Neo4j:

MERGE nodes (avoid duplicates using deterministic IDs):
  - User nodes: user_{user_id}
  - Resource nodes: resource_{type}_{id}
  - Request nodes: request_{hash}

CREATE relationships using Cypher queries


┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 4: IDOR DETECTION                                            │
└─────────────────────────────────────────────────────────────────────┘

Query Neo4j to find IDOR patterns:

// Find cross-user resource access
MATCH (u1:User)<-[:AUTHENTICATED_AS]-(r1:Request)-[:ACCESSES]->(res:Resource)
MATCH (u2:User)<-[:AUTHENTICATED_AS]-(r2:Request)-[:ACCESSES]->(res)
WHERE u1.user_id <> u2.user_id
RETURN u1.user_id, u2.user_id, res.resource_id
```

### 3.2. Mô hình Graph Database

**Graph Schema:**

```
                    ┌──────────────┐
                    │   Endpoint   │
                    │              │
                    │ path         │
                    │ method       │
                    │ type         │
                    └──────────────┘
                           ^
                           │
                      [:TARGETS]
                           │
    ┌──────────────┐      │      ┌──────────────┐
    │     User     │      │      │   Resource   │
    │              │      │      │              │
    │ user_id      │      │      │ resource_id  │
    │ username     │      │      │ resource_type│
    │ auth_method  │      │      │ operation    │
    └──────────────┘      │      └──────────────┘
           ^              │              ^
           │              │              │
  [:AUTHENTICATED_AS]  ┌──┴───────┐  [:ACCESSES]
           │            │ Request  │     │
           └────────────│          │─────┘
                        │ method   │
                        │ url      │
                        │ timestamp│
                        └──────────┘
                           │   ^
                           │   │
                   [:FOLLOWS]  │
                           │   │
                           v   │
                        ┌──────────┐
                        │ Request  │
                        │  (next)  │
                        └──────────┘
```

**Các node types:**

| Node | Properties | Description |
|------|------------|-------------|
| `User` | user_id, username, auth_method | Người dùng thực hiện request |
| `Resource` | resource_id, resource_type, operation | Tài nguyên được truy cập |
| `Request` | method, url, timestamp, protocol | HTTP request |
| `Parameter` | name, value, type, location | Query/path parameters |
| `Header` | name, value, category | HTTP headers (AUTH only) |
| `Endpoint` | path, method, domain, type | API endpoint |

**Các relationship types:**

| Relationship | Direction | Ý nghĩa |
|--------------|-----------|---------|
| `AUTHENTICATED_AS` | Request → User | Request được thực hiện bởi User nào |
| `ACCESSES` | Request → Resource | Request truy cập Resource nào |
| `TARGETS` | Request → Endpoint | Request gọi tới Endpoint nào |
| `FOLLOWS` | Request → Request | Request này theo sau Request trước (cùng user) |
| `HAS_PARAMETER` | Request → Parameter | Request có Parameter nào |
| `HAS_HEADER` | Request → Header | Request có Header nào |

### 3.3. Ví dụ cụ thể

**Input: 2 HTTP Requests**

```
Request 1:
GET /api/users/123
Authorization: Bearer <user_id=5, username="alice">

Request 2:
GET /api/users/123  
Authorization: Bearer <user_id=10, username="bob">
```

**Graph tạo ra:**

```cypher
// Nodes
(alice:User {user_id: "5", username: "alice"})
(bob:User {user_id: "10", username: "bob"})
(req1:Request {method: "GET", url: "/api/users/123", timestamp: "T1"})
(req2:Request {method: "GET", url: "/api/users/123", timestamp: "T2"})
(res:Resource {resource_id: "123", resource_type: "user"})
(ep:Endpoint {path: "/api/users/123", method: "GET"})

// Relationships
(req1)-[:AUTHENTICATED_AS]->(alice)
(req2)-[:AUTHENTICATED_AS]->(bob)
(req1)-[:ACCESSES]->(res)
(req2)-[:ACCESSES]->(res)  // ⚠️ IDOR detected!
(req1)-[:TARGETS]->(ep)
(req2)-[:TARGETS]->(ep)
```

**IDOR Detection Query:**

```cypher
MATCH (alice)<-[:AUTHENTICATED_AS]-(req1)-[:ACCESSES]->(res)
MATCH (bob)<-[:AUTHENTICATED_AS]-(req2)-[:ACCESSES]->(res)
WHERE alice.user_id <> bob.user_id
RETURN alice.user_id AS attacker,
       bob.user_id AS victim, 
       res.resource_id AS compromised_resource
       
// Result: Alice và Bob cùng truy cập resource "123" → Potential IDOR!
```

### 3.4. Tính năng Request Ordering (FOLLOWS)

**Mục đích:**  
Theo dõi chuỗi requests của mỗi user để phát hiện automation/attack patterns.

**Cách hoạt động:**

```python
# RuleBasedGraphLoader tracks last request per user
self.user_last_request = {}  # {user_id: (request_id, timestamp)}

# When processing new request:
if user_id in self.user_last_request:
    prev_request_id, prev_timestamp = self.user_last_request[user_id]
    
    # Create FOLLOWS edge
    CREATE (prev_request)-[:FOLLOWS {time_delta: seconds}]->(current_request)
    
# Update tracking
self.user_last_request[user_id] = (current_request_id, current_timestamp)
```

**Ví dụ sử dụng:**

```cypher
// Tìm user có requests quá nhanh (automation/bot)
MATCH (r1)-[f:FOLLOWS]->(r2)
WHERE f.time_delta < 1  // < 1 second
MATCH (u:User)<-[:AUTHENTICATED_AS]-(r1)
RETURN u.user_id, count(*) AS rapid_requests
ORDER BY rapid_requests DESC
```

---

## 4. HƯỚNG PHÁT TRIỂN TIẾP THEO

### 4.1. Tính năng hiện tại chưa hoàn thiện

#### 4.1.1. Active IDOR Testing Module

**Vấn đề:**  
Hiện tại chỉ **passive analysis** (phân tích traffic có sẵn), chưa test chủ động.

**Đề xuất:**  
Thêm module tự động test IDOR:

```python
class IDORTester:
    def test_cross_user_access(self):
        # 1. Collect user-resource mappings from graph
        user_resources = self.get_user_resource_map()
        
        # 2. Try cross-user access
        for user_a, resources_a in user_resources.items():
            for user_b in users:
                if user_a != user_b:
                    for resource in resources_a:
                        # Try accessing with wrong user
                        vulnerable = self.test_access(user_b.token, resource)
                        if vulnerable:
                            self.report_idor(user_a, user_b, resource)
```

**Lợi ích:**
- Xác nhận IDOR thực tế (không chỉ nghi ngờ)
- Tự động hóa penetration testing
- Tạo PoC (Proof of Concept) cho báo cáo

#### 4.1.2. Machine Learning for Pattern Detection

**Vấn đề:**  
Rule-based không phát hiện được các pattern phức tạp chưa được định nghĩa.

**Đề xuất:**  
Sử dụng Graph Neural Networks (GNN) để học patterns:

```python
# Train GNN trên graph
model = GraphSAGE(input_dim=node_features, hidden_dim=64, output_dim=2)

# Predict IDOR probability
for (user, resource) pair:
    score = model.predict_idor_probability(user, resource, graph_context)
    if score > threshold:
        flag_as_potential_idor()
```

**Datasets:**
- Sử dụng các vulnerable apps (DVWA, WebGoat, Juice Shop)
- Thu thập traffic và label IDOR manually

### 4.2. Cải tiến kiến trúc

#### 4.2.1. Distributed Processing

**Vấn đề:**  
Xử lý tuần tự, không scale với high-traffic applications.

**Đề xuất:**  
Sử dụng message queue (RabbitMQ/Kafka):

```
BurpSuite → Flask → RabbitMQ → Multiple Workers → Neo4j
                         │
                         └──> Worker 1
                         └──> Worker 2  
                         └──> Worker 3
```

#### 4.2.2. Real-time Alert System

**Đề xuất:**  
Thêm WebSocket/SSE để alert real-time khi phát hiện IDOR:

```python
@app.route('/alerts/stream')
def alert_stream():
    def generate():
        while True:
            idor_alerts = detect_idor_patterns()
            for alert in idor_alerts:
                yield f"data: {json.dumps(alert)}\n\n"
    return Response(generate(), mimetype='text/event-stream')
```

#### 4.2.3. Web Dashboard

**Đề xuất:**  
Tạo web interface để visualize và quản lý:

```
React Frontend
  ├── Graph Visualization (D3.js / Cytoscape.js)
  ├── IDOR Alert Dashboard
  ├── User Journey View
  ├── Statistics & Reports
  └── Configuration Manager
```

### 4.3. Tối ưu hiệu suất

#### 4.3.1. Graph Indexing

```cypher
// Tạo indexes cho truy vấn nhanh
CREATE INDEX user_id_index FOR (u:User) ON (u.user_id);
CREATE INDEX resource_id_index FOR (r:Resource) ON (r.resource_id, r.resource_type);
CREATE INDEX request_timestamp_index FOR (req:Request) ON (req.timestamp);
```

#### 4.3.2. Query Optimization

**Thay vì:**
```cypher
// Slow - full graph scan
MATCH (u1:User)<-[:AUTHENTICATED_AS]-(r1)-[:ACCESSES]->(res)
MATCH (u2:User)<-[:AUTHENTICATED_AS]-(r2)-[:ACCESSES]->(res)
WHERE u1.user_id <> u2.user_id
```

**Tối ưu:**
```cypher
// Fast - use index
MATCH (res:Resource {resource_id: $target_id})
MATCH (res)<-[:ACCESSES]-(r:Request)-[:AUTHENTICATED_AS]->(u:User)
WITH res, collect(DISTINCT u.user_id) AS users
WHERE size(users) > 1
RETURN res, users
```

#### 4.3.3. Caching Layer

Thêm Redis để cache:
- User sessions
- Frequently accessed resources
- Common query results

### 4.4. Tích hợp với các công cụ khác

#### 4.4.1. CI/CD Integration

```yaml
# .github/workflows/security-scan.yml
name: IDOR Detection
on: [pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Run IDOR tests
        run: |
          docker-compose up -d idor-detector
          python run_idor_tests.py
          docker-compose down
```

#### 4.4.2. SIEM Integration

Export alerts tới Splunk/ELK:

```python
def send_to_siem(idor_finding):
    siem_event = {
        "severity": "HIGH",
        "type": "IDOR_DETECTED",
        "user": finding.attacker_id,
        "resource": finding.resource_id,
        "timestamp": datetime.utcnow()
    }
    requests.post(SIEM_ENDPOINT, json=siem_event)
```

### 4.5. Mở rộng phạm vi phát hiện

#### 4.5.1. API Authorization Analysis

Phân tích logic authorization phức tạp:
- Role-based access control (RBAC)
- Attribute-based access control (ABAC)
- Multi-tenant isolation

#### 4.5.2. WebSocket/GraphQL Support

Hiện tại chỉ support REST APIs, cần mở rộng:
- WebSocket messages
- GraphQL queries
- gRPC calls

### 4.6. Research Directions

#### 4.6.1. Academic Research

**Đề tài nghiên cứu tiềm năng:**
1. "Graph-based IDOR Detection using Temporal Analysis"
2. "Automated Authorization Testing via Graph Traversal"
3. "GNN for Web Security Vulnerability Detection"

#### 4.6.2. Benchmark Dataset

Tạo public dataset cho IDOR research:
- Annotated HTTP traffic
- Known IDOR vulnerabilities
- Graph representations
- Test cases

---

## 5. KẾT LUẬN

### 5.1. Đóng góp của đề tài

Hệ thống đã xây dựng thành công:

✅ **Rule-based parser** cho phân tích HTTP requests real-time  
✅ **Graph database model** để biểu diễn quan hệ User-Request-Resource  
✅ **User & Resource extraction** từ JWT/cookies và URL patterns  
✅ **Temporal ordering** với FOLLOWS relationships  
✅ **IDOR detection queries** đơn giản và hiệu quả  

### 5.2. Hạn chế

❌ Chỉ **passive analysis**, chưa có active testing  
❌ Rule-based có thể miss các patterns phức tạp  
❌ Chưa có UI/dashboard trực quan  
❌ Chưa scale cho high-traffic environments  

### 5.3. Ý nghĩa thực tiễn

**Ứng dụng:**
- Kiểm thử bảo mật ứng dụng web
- Penetration testing automation
- Security audit và compliance
- Research và education

**Giá trị:**
- Giảm thời gian manual testing
- Phát hiện IDOR một cách có hệ thống
- Visualization giúp hiểu rõ attack surface
- Open-source, dễ customize

---

## 6. TÀI LIỆU THAM KHẢO

### Books
1. OWASP Testing Guide v4.2 (2020). "Testing for Insecure Direct Object References"
2. Neo4j Graph Data Science (2021). "Graph Algorithms for Security Analysis"

### Papers
1. Pellegrino, G., et al. (2018). "Automatic Extraction of Access Control Policies from Applications"
2. Sabelfeld, A., & Myers, A. C. (2003). "Language-based information-flow security"

### Online Resources
1. OWASP Top 10 - 2021: https://owasp.org/Top10/
2. Neo4j Documentation: https://neo4j.com/docs/
3. BurpSuite Professional: https://portswigger.net/burp/documentation

### Tools & Frameworks
1. Neo4j Graph Database 5.15.0
2. Flask Web Framework 3.0.0
3. Python 3.11
4. Docker & Docker Compose

---

**Ngày hoàn thành:** [Ngày/Tháng/Năm]

**Chữ ký sinh viên**

---

## PHỤ LỤC

### A. Cài đặt và sử dụng

```bash
# 1. Clone repository
git clone <repository-url>
cd project3-idor

# 2. Cấu hình environment
cp .env.example .env

# 3. Build và chạy
docker compose up --build -d

# 4. Kiểm tra
curl http://localhost:5000/health
```

### B. Ví dụ queries

```cypher
-- 1. Tìm IDOR
MATCH (u1:User)<-[:AUTHENTICATED_AS]-(r1)-[:ACCESSES]->(res:Resource)
MATCH (u2:User)<-[:AUTHENTICATED_AS]-(r2)-[:ACCESSES]->(res)
WHERE u1.user_id <> u2.user_id
RETURN u1.user_id, u2.user_id, res.resource_id;

-- 2. User journey
MATCH path = (u:User)<-[:AUTHENTICATED_AS]-(r1:Request)-[:FOLLOWS*]->(r2:Request)
WHERE u.user_id = "5"
RETURN path;

-- 3. Statistics
MATCH (u:User) RETURN count(u) AS total_users;
MATCH (r:Resource) RETURN r.resource_type, count(*) AS count;
```

### C. Cấu trúc thư mục dự án

```
project3-idor/
├── config/
│   └── parsing_rules.yaml      # YAML rules configuration
├── src/
│   ├── parsers/
│   │   └── yaml_rule_parser.py # Rule-based parser
│   ├── graph_db/
│   │   ├── neo4j_client.py     # Neo4j connection
│   │   └── rule_based_loader.py # Graph loader
│   ├── models/
│   │   ├── http_models.py      # HTTP data models
│   │   └── graph_models.py     # Graph node models
│   └── server/
│       └── app.py              # Flask application
├── docker-compose.yml          # Docker configuration
├── Dockerfile                  # Neo4j Dockerfile
├── Dockerfile.app              # Flask Dockerfile
├── main.py                     # Main entry point
└── requirements.txt            # Python dependencies
```
