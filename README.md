# Neunet AI Services

A powerful backend service that handles job postings, candidate applications, and AI-powered candidate matching for the Neunet platform.

## Tech Stack

### Backend Framework
- FastAPI (v0.104.1) - Modern, fast web framework for building APIs with Python
- Uvicorn (v0.24.0) - Lightning-fast ASGI server implementation

### Database
- Azure Cosmos DB (v4.5.1) - Globally distributed, multi-model database service
- Multiple containers for different data types:
  - Job descriptions
  - Applications
  - Resumes
  - GitHub analysis
  - Rankings
  - Questionnaires

### Authentication & Security
- Python-Jose (v3.3.0) - JavaScript Object Signing and Encryption implementation
- Passlib (v1.7.4) - Password hashing library
- BCrypt (v4.0.1) - Password hashing

### Data Validation
- Pydantic (v2.4.2) - Data validation using Python type annotations

## Project Structure

```
neunet-ai-services/
├── common/
│   ├── database/
│   │   └── cosmos/         # Cosmos DB operations
│   └── utils/             # Utility functions
├── config/
│   └── config.yaml        # Configuration settings
├── services/
│   └── api/
│       └── main.py        # FastAPI application
├── scripts/
│   └── run_api.sh        # Server startup script
├── requirements.txt      # Python dependencies
└── README.md
```

## Features

1. Job Management
   - Create and manage job postings
   - Store job descriptions and requirements
   - Handle job questionnaires

2. Application Processing
   - Process candidate applications
   - Store resumes and cover letters
   - Track application status

3. Candidate Analysis
   - GitHub profile analysis
   - Resume parsing
   - Candidate ranking

## API Endpoints

### Jobs
- `POST /jobs/` - Create a new job posting
- `GET /jobs/{job_id}` - Get job details
- `GET /jobs/` - List all jobs

### Applications
- `POST /jobs/{job_id}/apply` - Submit job application
- `GET /jobs/{job_id}/applications` - Get job applications
- `GET /debug/candidates/{job_id}` - Get candidates for a job

## Deployment

The API is deployed to Azure App Service and can be accessed at https://neunet-api.azurewebsites.net.

## Deployment Status

Deployed to Azure App Service at: https://neunet-api.azurewebsites.net

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure Azure Cosmos DB settings in `config/config.yaml`
4. Run the server:
   ```bash
   ./scripts/run_api.sh
   ```

## Configuration

The application uses a YAML configuration file (`config/config.yaml`) for:
- Database connection settings
- Container names
- API configurations

## Development

1. Start the development server:
   ```bash
   cd services/api
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. The API will be available at `http://localhost:8000`

## Security

- Implements secure password hashing with BCrypt
- Uses JWT for authentication
- Supports CORS for frontend integration

## Getting Started

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Run locally:**
   ```
   uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be available at `http://localhost:8000`.

3. **Run with Docker:**
   ```
   docker build -t neunet-backend .
   docker run -p 8000:8000 neunet-backend
   ```

## Deployment

- Deploy to [Render](https://render.com/) or your preferred cloud provider.
- Set all required environment variables (DB credentials, API keys, etc.) in the Render dashboard.
- Make sure your CORS settings in `services/api/main.py` include your deployed frontend domain (e.g., `https://neunet.io` or `https://www.neunet.io`).
- After deployment, your API will be available at your Render URL (e.g., `https://neunet-ai-services.onrender.com`).

## API Documentation

- Interactive Swagger UI: `/docs` (e.g., `https://neunet-ai-services.onrender.com/docs`)
- Redoc documentation: `/redoc`

## Notes

- Ensure `.gitignore` is configured to avoid uploading caches, local config, and secrets.
- Do **not** commit your `.env` file or credentials to GitHub.
- Check backend logs on Render if you encounter errors after deployment.