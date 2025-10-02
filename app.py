from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.ai_job_description.generate_description import generate_description
from services.auth import auth_router

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "https://neunet.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobDescriptionRequest(BaseModel):
    title: str = None
    company_name: str = None
    location: str = None
    type: str = None
    time_commitment: str = None
    description: str = None
    requirements: str = None
    job_id: str = None

router = APIRouter()

@router.post("/api/generate-job-description")
def generate_job_description(request: JobDescriptionRequest):
    try:
        data = request.dict()
        generated = generate_description(data)
        return {"job_description": generated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include routers
app.include_router(router)
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
