# Authentication System

This authentication system uses:
- **FastAPI** for the backend API
- **Azure Cosmos DB** for user storage
- **JWT tokens** for authentication
- **bcrypt** for password hashing

## Setup

1. Make sure your `.env` file has the Cosmos DB credentials:
```
COSMOS_DB_URI=https://neunet-cosmos-db.documents.azure.com:443/
COSMOS_DB_KEY=your-key-here
COSMOS_DB_NAME=CandidateInfoDB
```

2. Install dependencies (already in requirements.txt):
```bash
pip install fastapi uvicorn python-jose passlib bcrypt azure-cosmos python-dotenv
```

3. Run the backend:
```bash
cd /Users/astha/Neunet-Backend-deployment
python app.py
```

## API Endpoints

### POST /api/auth/signup
Create a new user account.

**Request Body:**
```json
{
  "name": "John Doe",
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword",
  "company_size": "11-50"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "name": "John Doe",
    "username": "johndoe",
    "email": "john@example.com",
    "company_size": "11-50",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

### POST /api/auth/login
Login with existing credentials.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Response:** Same as signup

### GET /api/auth/me?token=<jwt_token>
Get current user information.

## Frontend Integration

The frontend uses the `authService` in `/src/services/authService.ts` to:
1. Call the backend API
2. Store JWT token in localStorage
3. Include token in authenticated requests

## Database Structure

Users are stored in Cosmos DB with the following schema:
```json
{
  "id": "uuid",
  "name": "string",
  "username": "string",
  "email": "string (partition key)",
  "hashed_password": "string",
  "company_size": "string",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```
