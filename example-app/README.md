# IDOR Vulnerable API - For Testing Only

⚠️ **WARNING**: This application contains intentional security vulnerabilities (IDOR - Insecure Direct Object Reference). It is designed for educational purposes and security testing tools development only. **DO NOT** deploy this in production or expose it to the internet.

## Description

This is a Node.js Express API with authentication that intentionally includes IDOR vulnerabilities. It's designed to help you test and develop tools that detect IDOR vulnerabilities in APIs.

## Features

- JWT-based authentication
- Multiple API endpoints with IDOR vulnerabilities
- In-memory database with sample data
- Docker support for easy deployment
- Comprehensive API documentation

## IDOR Vulnerabilities Included

This API contains the following intentional IDOR vulnerabilities:

### 1. **User Endpoints** (`/api/users/:id`)
- ✅ `GET /api/users/:id` - View any user's details
- ✅ `PUT /api/users/:id` - Update any user's information (including privilege escalation)
- ✅ `DELETE /api/users/:id` - Delete any user account

### 2. **Profile Endpoints** (`/api/profiles/:id`)
- ✅ `GET /api/profiles/:id` - Access any user's profile with sensitive PII (SSN, address, DOB)
- ✅ `PUT /api/profiles/:id` - Modify any user's profile
- ✅ `GET /api/profiles/user/:userId` - Access profile by user ID

### 3. **Document Endpoints** (`/api/documents/:id`)
- ✅ `GET /api/documents/:id` - Read any user's private documents
- ✅ `PUT /api/documents/:id` - Modify any user's documents
- ✅ `DELETE /api/documents/:id` - Delete any user's documents

### 4. **Order Endpoints** (`/api/orders/:id`)
- ✅ `GET /api/orders/:id` - View any user's orders (including shipping addresses)
- ✅ `PUT /api/orders/:id` - Modify any order (status, shipping address)
- ✅ `DELETE /api/orders/:id` - Cancel any user's orders

### 5. **Message Endpoints** (`/api/messages/:id`)
- ✅ `GET /api/messages/:id` - Read any user's private messages
- ✅ `DELETE /api/messages/:id` - Delete any message
- ✅ `PATCH /api/messages/:id/read` - Mark any message as read

## Setup and Installation

### Using Docker (Recommended)

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **The API will be available at:**
   ```
   http://localhost:3000
   ```

### Manual Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Create a `.env` file:**
   ```bash
   PORT=3000
   JWT_SECRET=your-secret-key-change-in-production
   NODE_ENV=development
   ```

3. **Start the server:**
   ```bash
   npm start
   ```

   Or for development with auto-reload:
   ```bash
   npm run dev
   ```

## Pre-configured Users

The application comes with 4 pre-configured users:

| Username | Password    | Role  | User ID |
|----------|-------------|-------|---------|
| alice    | password123 | user  | 1       |
| bob      | password123 | user  | 2       |
| charlie  | password123 | admin | 3       |
| dave     | password123 | user  | 4       |

## API Usage Examples

### 1. Register (Optional - if you want to create new users)
```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "password123"
  }'
```

Response will include a JWT token:
```json
{
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "role": "user"
  }
}
```

### 3. Exploit IDOR Vulnerabilities

Use the token from login in subsequent requests:

#### View another user's profile (IDOR):
```bash
# Alice (user ID 1) viewing Bob's profile (user ID 2)
curl -X GET http://localhost:3000/api/profiles/2 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### Read another user's document (IDOR):
```bash
# Alice (user ID 1) reading Bob's document (document ID 2)
curl -X GET http://localhost:3000/api/documents/2 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### View another user's order (IDOR):
```bash
# Alice viewing Bob's order
curl -X GET http://localhost:3000/api/orders/1002 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### Modify another user's profile (IDOR):
```bash
# Alice modifying Bob's profile
curl -X PUT http://localhost:3000/api/profiles/2 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Modified",
    "lastName": "Name"
  }'
```

#### Privilege escalation (IDOR):
```bash
# Alice upgrading herself to admin
curl -X PUT http://localhost:3000/api/users/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

## Testing Your IDOR Detection Tool

### Expected Behavior for IDOR Detection

Your tool should detect the following patterns:

1. **Sequential ID enumeration**: IDs are predictable integers (1, 2, 3...)
2. **Missing authorization**: Endpoints return data for any ID without checking ownership
3. **Status code analysis**: 
   - 200 OK = Resource exists and was accessed (potential IDOR)
   - 404 Not Found = Resource doesn't exist
   - 401 Unauthorized = No token provided
   - 403 Forbidden = Token invalid (not used for authorization)

### Test Scenarios

1. **Login as Alice (ID: 1)**
2. **Attempt to access resources with IDs 2, 3, 4** (other users)
3. **Compare responses**:
   - If you get 200 OK with data belonging to another user → IDOR vulnerability confirmed
   - If you get 403 Forbidden → Proper authorization in place

### Vulnerable Endpoints to Test

```
GET    /api/users/:id
PUT    /api/users/:id
DELETE /api/users/:id
GET    /api/profiles/:id
PUT    /api/profiles/:id
GET    /api/profiles/user/:userId
GET    /api/documents/:id
PUT    /api/documents/:id
DELETE /api/documents/:id
GET    /api/orders/:id
PUT    /api/orders/:id
DELETE /api/orders/:id
GET    /api/messages/:id
DELETE /api/messages/:id
PATCH  /api/messages/:id/read
```

## Project Structure

```
.
├── server.js              # Main application entry point
├── package.json           # Dependencies and scripts
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── .env                  # Environment variables
├── middleware/
│   └── auth.js          # JWT authentication middleware
├── routes/
│   ├── auth.js          # Authentication routes
│   ├── users.js         # User management (vulnerable)
│   ├── profiles.js      # Profile management (vulnerable)
│   ├── documents.js     # Document management (vulnerable)
│   ├── orders.js        # Order management (vulnerable)
│   └── messages.js      # Message management (vulnerable)
└── data/
    └── database.js      # In-memory database with sample data
```

## How to Fix IDOR Vulnerabilities

For educational purposes, here's how these vulnerabilities should be fixed:

```javascript
// BEFORE (Vulnerable):
router.get('/:id', authenticateToken, (req, res) => {
  const document = database.documents.find(d => d.id === parseInt(req.params.id));
  res.json(document);
});

// AFTER (Secure):
router.get('/:id', authenticateToken, (req, res) => {
  const document = database.documents.find(d => d.id === parseInt(req.params.id));
  
  // Check ownership
  if (document.userId !== req.user.id) {
    return res.status(403).json({ error: 'Access denied' });
  }
  
  res.json(document);
});
```

## Stopping the Application

### Docker:
```bash
docker-compose down
```

### Manual:
Press `Ctrl+C` in the terminal where the server is running.

## License

This project is for educational purposes only. Use at your own risk.

## Disclaimer

This application is intentionally vulnerable and should never be deployed in a production environment or exposed to the internet. It is designed solely for security testing and educational purposes.
