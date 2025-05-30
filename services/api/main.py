print("=== LOADING main.py ===")
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import random
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.database.cosmos import db_operations
from azure.storage.blob import BlobServiceClient
import io

app = FastAPI(title="Neunet Recruitment API")

# ------------------- Resume Parser Endpoint -------------------
from fastapi import UploadFile, File
import shutil
import tempfile
from services.resume_parser.parser.openai_resume_parser import parse_resume_json
from services.resume_parser.parser.pdf_parser import parse_pdf
from services.resume_parser.parser.doc_parser import parse_doc

@app.post("/api/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    import shutil, tempfile, os
    suffix = os.path.splitext(file.filename)[-1].lower()
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)  # Close the file descriptor immediately
    try:
        with open(temp_path, "wb") as out_file:
            shutil.copyfileobj(file.file, out_file)
        await file.close()
        import os
        print(f"[DEBUG] temp_path: {temp_path}")
        print(f"[DEBUG] os.getcwd(): {os.getcwd()}")
        if suffix == '.pdf':
            text, hyperlinks = parse_pdf(temp_path)
        elif suffix in ['.doc', '.docx']:
            text, hyperlinks = parse_doc(temp_path)
        else:
            return {"success": False, "data": None, "error": "Unsupported file format. Please upload PDF or DOCX."}
        extracted_info = parse_resume_json(text, hyperlinks)
        return {"success": True, "data": extracted_info, "error": None}
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.neunet.io",      # Production (www)
        "https://neunet.io",          # Production (non-www)
        "http://localhost:5173",      # Local Vite dev server
        "http://localhost:8000",      # Local FastAPI (if needed)
    ],  # Allow production and local dev

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobQuestionnaire(BaseModel):
    questions: List[str]

class JobDescription(BaseModel):
    title: str
    location: str
    job_type: str
    description: str
    requirements: str
    responsibilities: str
    salary_range: str
    benefits: Optional[str] = None
    company_culture: Optional[str] = None
    interview_process: Optional[str] = None
    growth_opportunities: Optional[str] = None
    tech_stack: Optional[str] = None
    questionnaire: Optional[JobQuestionnaire] = None
    job_id: str = Field(default_factory=lambda: str(random.randint(100000, 999999)))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator('job_id')
    def validate_job_id(cls, v):
        if not (len(v) == 6 and v.isdigit()):
            raise ValueError('job_id must be a 6-digit number')
        return v

class CandidateRanking(BaseModel):
    job_id: str
    candidate_email: str
    ranking: float
    conversation: str
    resume: dict

class CandidateApplication(BaseModel):
    name: str
    email: str
    resume: str
    cover_letter: Optional[str] = None
    ranking: float = Field(default=0.0)  # For testing, we'll set a default ranking

class JobDescriptionRequest(BaseModel):
    title: str = None
    company_name: str = None
    location: str = None
    type: str = None
    time_commitment: str = None
    description: str = None
    requirements: str = None
    job_id: str = None

# Job Description Endpoints
@app.get("/jobs/")
async def list_jobs():
    try:
        print("Fetching all jobs...")  # Debug log
        jobs = db_operations.fetch_all_jobs()
        print(f"Fetched jobs: {jobs}")  # Debug log
        return jobs if jobs else []
    except Exception as e:
        print(f"Error fetching jobs: {e}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/")
async def create_job(job: JobDescription, background_tasks: BackgroundTasks):
    try:
        # Generate a new 6-digit job ID if not provided
        if not job.job_id:
            job.job_id = str(random.randint(100000, 999999))
        
        job_data = job.dict()
        job_data["id"] = job_data["job_id"]  # Ensure id is set for Cosmos DB
        
        print("Creating job with data:", job_data)  # Debug log
        
        # Store in Cosmos DB
        db_operations.upsert_jobDetails(job_data)

        # Trigger questionnaire generation as a background task
        background_tasks.add_task(generate_and_store_questionnaire, job.job_id)

        return {"message": "Job created successfully", "job_id": job.job_id}
    except Exception as e:
        print(f"Error creating job: {e}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

# --- Background Task for Questionnaire Generation ---
def generate_and_store_questionnaire(job_id):
    try:
        from services.resume_ranking.job_description_questionnaire.jd_questionnaire_generator import generate_questionnaire
        from common.database.cosmos.db_operations import fetch_job_description, store_job_questionnaire, upsert_jobDetails
        import json
        import datetime
        job_description = fetch_job_description(job_id)
        if not job_description:
            print(f"[ERROR] Could not fetch job description for job_id: {job_id}")
            return
        print(f"[INFO] Generating questionnaire for job_id: {job_id}")
        raw_response = generate_questionnaire(job_description)
        start_idx = raw_response.find("{")
        end_idx = raw_response.rfind("}")
        try:
            json_data = json.loads(raw_response[start_idx:end_idx+1])
        except Exception as e:
            print(f"[ERROR] Failed to parse questionnaire JSON: {e}")
            return
        json_data['job_id'] = job_id
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = f"{job_id}_{current_time}"
        json_data['id'] = unique_id
        store_job_questionnaire(json_data)
        # Optionally, attach questionnaire to job record
        job_description['questionnaire'] = json_data
        upsert_jobDetails(job_description)
        print(f"[INFO] Questionnaire generated and stored for job_id: {job_id}")
    except Exception as e:
        print(f"[ERROR] Exception in background questionnaire generation: {e}")

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        job = db_operations.fetch_job_description(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}/questionnaire")
async def get_job_questionnaire(job_id: str):
    try:
        job = db_operations.fetch_job_description(job_id)
        if job and job.get("questionnaire"):
            return job["questionnaire"]
        # If not found in job document, look in jobDescriptionQuestionnaire container
        questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
        if questionnaire_doc and questionnaire_doc.get("questionnaire"):
            return questionnaire_doc["questionnaire"]
        raise HTTPException(status_code=404, detail="Questionnaire not found")
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Candidate Endpoints
@app.get("/jobs/{job_id}/candidates")
async def get_job_candidates(job_id: str, top_k: int = 10):
    try:
        candidates = db_operations.fetch_top_k_candidates_by_count(job_id, top_k)
        if not candidates:
            return []
        # Fetch all rankings for this job in one go
        rankings_map = { (job_id, k.strip().lower()): v for k, v in db_operations.fetch_candidate_rankings(job_id).items() }
        print(f"[DEBUG] rankings_map for job {job_id}: {rankings_map}")
        patched_candidates = []
        for cand in candidates:
            resume = None
            if 'parsed_resume' in cand and cand['parsed_resume']:
                resume = cand['parsed_resume']
            elif 'resume' in cand and cand['resume']:
                resume = cand['resume']
            cand = dict(cand)
            cand['resume'] = resume
            # Normalize email for lookup
            email = (cand.get('email') or '').strip().lower()
            print(f"[DEBUG] Checking candidate email: {email}")
            if email and (job_id, email) in rankings_map:
                # Always pick ranking and explanation directly from ranking container
                raw_ranking = rankings_map[(job_id, email)].get('ranking', 0)
                explanation = rankings_map[(job_id, email)].get('explanation', None)
                if isinstance(raw_ranking, (float, int)) and 0 < raw_ranking <= 1:
                    cand['ranking'] = round(raw_ranking * 100)
                else:
                    cand['ranking'] = round(raw_ranking)
                cand['explanation'] = explanation
            else:
                cand['ranking'] = 0
                cand['explanation'] = None
            patched_candidates.append(cand)
        return patched_candidates
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates/{candidate_id}")
async def get_candidate_by_id(candidate_id: str):
    """
    Return candidate profile and all jobs they've applied to.
    candidate_id can be email or unique candidate id.
    """
    try:
        # Fetch all applications for this candidate by candidate_id and by email, merge and deduplicate
        applications_by_id = db_operations.fetch_applications_by_candidate(candidate_id) or []
        applications_by_email = db_operations.fetch_applications_by_candidate_email(candidate_id) or []
        # Merge and deduplicate by (job_id, email)
        seen = set()
        all_applications = []
        for app in applications_by_id + applications_by_email:
            key = (app.get('job_id'), app.get('email'))
            if key not in seen:
                seen.add(key)
                all_applications.append(app)
        if not all_applications:
            raise HTTPException(status_code=404, detail="Candidate not found")
        # Profile fields from one application (assuming all have same candidate info)
        profile_fields = [
            'name', 'email', 'avatar', 'role', 'evaluation', 'github', 'skills', 'resume', 'resume_blob_name', 'cover_letter', 'ranking'
        ]
        candidate_profile = {k: all_applications[0].get(k) for k in profile_fields if k in all_applications[0]}
        # List of jobs applied to
        jobs_applied = []
        for app in all_applications:
            job_id = app.get('job_id')
            job_title = app.get('job_title')
            email = app.get('email')
            # Patch: Always fetch job title if missing
            if not job_title and job_id:
                job_desc = db_operations.fetch_job_description(job_id)
                job_title = job_desc['title'] if job_desc and 'title' in job_desc else job_id
            # Fetch ranking and explanation from ranking container
            ranking = 0.0
            explanation = None
            if job_id and email:
                rmap = db_operations.fetch_candidate_rankings(job_id)
                if email in rmap:
                    ranking = rmap[email].get('ranking', 0.0)
                    explanation = rmap[email].get('explanation')
            jobs_applied.append({
                'job_id': job_id,
                'title': job_title,
                'status': app.get('status'),
                'applied_at': app.get('applied_at'),
                'ranking': ranking,
                'explanation': explanation,
                'resume_blob_name': app.get('resume_blob_name'),
                'score': app.get('score') or ranking,
            })
        candidate_profile['jobsApplied'] = jobs_applied
        # Set profile ranking as highest ranking across jobs (or 0)
        candidate_profile['ranking'] = max([j['ranking'] for j in jobs_applied] or [0.0])
        # Add parsed_resume details if available (check both possible field names)
        parsed_resume = None
        if 'parsed_resume' in all_applications[0] and isinstance(all_applications[0]['parsed_resume'], dict):
            parsed_resume = all_applications[0]['parsed_resume']
            candidate_profile['parsed_resume'] = parsed_resume
        elif 'resume' in all_applications[0] and isinstance(all_applications[0]['resume'], dict):
            parsed_resume = all_applications[0]['resume']
            candidate_profile['parsed_resume'] = parsed_resume
        # Always set 'skills' from parsed_resume if available
        if parsed_resume and parsed_resume.get('skills'):
            candidate_profile['skills'] = parsed_resume['skills']
        # Add a unique candidate_id (use email for now if no id field)
        candidate_profile['candidate_id'] = all_applications[0].get('candidate_id') or all_applications[0].get('email')
        return candidate_profile
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/candidates/{candidate_email}/status")
async def update_candidate_status(job_id: str, candidate_email: str, status: str):
    try:
        db_operations.update_application_status(job_id, candidate_email, status)
        return {"message": "Status updated successfully"}
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates/{job_id}/{email}/resume")
async def get_candidate_resume(job_id: str, email: str):
    try:
        candidate = db_operations.fetch_resume_with_email_and_job(job_id, email)
        if not candidate or "resume_blob_name" not in candidate:
            raise HTTPException(status_code=404, detail="Resume not found")
        blob_name = candidate["resume_blob_name"]
        AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        CONTAINER_NAME = "resumes"
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob_name)
        stream = io.BytesIO()
        blob_data = blob_client.download_blob()
        blob_data.readinto(stream)
        stream.seek(0)
        return StreamingResponse(stream, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename={os.path.basename(blob_name)}"
        })
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Application Endpoints
@app.get("/applications/{job_id}")
async def get_job_applications(job_id: str):
    try:
        applications = db_operations.fetch_application_by_job_id(job_id)
        if not applications:
            return []
        return applications
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/apply")
async def apply_for_job(
    job_id: str,
    name: str = Form(...),
    email: str = Form(...),
    cover_letter: str = Form(None),
    ranking: float = Form(0.0),  # Will be overwritten by actual ranking logic
    resume: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    try:
        # Defensive logging and checks
        if resume is None:
            print("[ERROR] No resume file provided.")
            raise HTTPException(status_code=400, detail="No resume file provided.")
        if not hasattr(resume, 'filename') or resume.filename is None:
            print(f"[ERROR] Resume filename is missing or None. Resume object: {resume}")
            raise HTTPException(status_code=400, detail="Resume filename is missing.")
        print(f"[DEBUG] Received resume filename: {resume.filename}")
        AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        CONTAINER_NAME = "resumes"
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        ext = os.path.splitext(resume.filename)[-1]
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        blob_name = f"{email}_{timestamp}{ext}"
        blob_client = container_client.get_blob_client(blob_name)
        data = await resume.read()
        if data is None or len(data) == 0:
            print("[ERROR] Resume file is empty.")
            raise HTTPException(status_code=400, detail="Resume file is empty.")
        try:
            blob_client.upload_blob(data, overwrite=True)
            resume_blob_name = blob_name
        except Exception as upload_exc:
            print(f"[ERROR] Resume upload to Azure failed: {upload_exc}")
            resume_blob_name = None
        # Parse the uploaded resume and store extracted info (github/linkedin/etc)
        parsed_resume = None
        # Only proceed if the upload was successful
        if not resume_blob_name:
            raise HTTPException(status_code=500, detail="Resume upload failed. Please try again.")
        try:
            # Save file to temp
            import tempfile
            suffix = os.path.splitext(resume.filename)[-1].lower()
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(temp_path, "wb") as out_file:
                out_file.write(data)
            if suffix == '.pdf':
                text, hyperlinks = parse_pdf(temp_path)
            elif suffix in ['.doc', '.docx']:
                text, hyperlinks = parse_doc(temp_path)
            else:
                text, hyperlinks = '', []
            parsed_resume = parse_resume_json(text, hyperlinks)
        except Exception as e:
            print(f"[WARN] Resume parsing failed: {e}")
            parsed_resume = None
        finally:
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

        # --- Integrate Resume Ranking Logic ---
        # Fetch job description and questionnaire
        from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
        from common.database.cosmos import db_operations
        job_description = db_operations.fetch_job_description(job_id)
        job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
        job_questionnaire_id = job_questionnaire_doc['id'] if job_questionnaire_doc else None
        questionnaire = job_questionnaire_doc['questionnaire'] if job_questionnaire_doc else None
        resume_text = text if 'text' in locals() else ''
        job_description_text = job_description['description'] if job_description and 'description' in job_description else ''
        # Defensive: Only call ranking if all required fields are present
        ranking_score = ranking
        if all([job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire]):
            try:
                ranking_result = initiate_chat(job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire)
                # Try to extract a numeric score from the result (if possible)
                if isinstance(ranking_result, dict) and 'score' in ranking_result:
                    ranking_score = ranking_result['score']
                elif isinstance(ranking_result, (int, float)):
                    ranking_score = ranking_result
                elif isinstance(ranking_result, str):
                    import re
                    match = re.search(r"([0-9]+\.?[0-9]*)", ranking_result)
                    if match:
                        ranking_score = float(match.group(1))
            except Exception as e:
                print(f"[WARN] Resume ranking logic failed: {e}")
                ranking_score = ranking
        else:
            print("[WARN] Skipping ranking logic due to missing data.")

        application_data = {
            "id": f"{job_id}_{email}",
            "job_id": job_id,
            "name": name,
            "email": email,
            "cover_letter": cover_letter,
            "ranking": ranking,  # Initial placeholder, will update after ranking
            "status": "applied",
            "applied_at": datetime.utcnow().isoformat(),
            "resume_blob_name": resume_blob_name,
            "parsed_resume": parsed_resume,
            "type": "candidate",
        }
        from common.database.cosmos.db_operations import upsert_candidate
        upsert_candidate(application_data)

        # Trigger resume ranking as a background task
        if background_tasks is not None:
            background_tasks.add_task(rank_candidate_resume_task, job_id, email, resume_blob_name, parsed_resume)

        return {"message": "Application submitted successfully. Ranking will be available soon."}
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- Background Task for Resume Ranking ---
def rank_candidate_resume_task(job_id, email, resume_blob_name, parsed_resume):
    try:
        from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
        from common.database.cosmos import db_operations
        job_description = db_operations.fetch_job_description(job_id)
        job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
        job_questionnaire_id = job_questionnaire_doc['id'] if job_questionnaire_doc else None
        questionnaire = job_questionnaire_doc['questionnaire'] if job_questionnaire_doc else None
        # Download resume text from blob if needed (parsed_resume may be None)
        resume_text = ''
        if parsed_resume and isinstance(parsed_resume, dict) and 'raw_text' in parsed_resume:
            resume_text = parsed_resume['raw_text']
        else:
            # Try to download and parse again if needed
            try:
                AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                CONTAINER_NAME = "resumes"
                from azure.storage.blob import BlobServiceClient
                blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
                container_client = blob_service_client.get_container_client(CONTAINER_NAME)
                blob_client = container_client.get_blob_client(resume_blob_name)
                stream = blob_client.download_blob().readall()
                import tempfile
                suffix = os.path.splitext(resume_blob_name)[-1].lower()
                fd, temp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                with open(temp_path, "wb") as out_file:
                    out_file.write(stream)
                if suffix == '.pdf':
                    from services.resume_parser.parser.pdf_parser import parse_pdf
                    text, hyperlinks = parse_pdf(temp_path)
                elif suffix in ['.doc', '.docx']:
                    from services.resume_parser.parser.doc_parser import parse_doc
                    text, hyperlinks = parse_doc(temp_path)
                else:
                    text, hyperlinks = '', []
                resume_text = text
                os.remove(temp_path)
            except Exception as e:
                print(f"[WARN] Could not re-parse resume from blob: {e}")
                resume_text = ''
        job_description_text = job_description['description'] if job_description and 'description' in job_description else ''
        if all([job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire]):
            try:
                ranking_result = initiate_chat(job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire)
                ranking_score = None
                if isinstance(ranking_result, dict) and 'score' in ranking_result:
                    ranking_score = float(ranking_result['score'])
                elif isinstance(ranking_result, (float, int)):
                    ranking_score = float(ranking_result)
                else:
                    import re
                    match = re.search(r"([0-9]+\.?[0-9]*)", str(ranking_result))
                    if match:
                        ranking_score = float(match.group(1))
                if ranking_score is not None:
                    # Update candidate record with new ranking
                    candidate = db_operations.fetch_resume_with_email_and_job(job_id, email)
                    if candidate:
                        candidate['ranking'] = ranking_score
                        db_operations.upsert_candidate(candidate)
                        print(f"[INFO] Ranking updated for {email} in job {job_id}: {ranking_score}")
            except Exception as e:
                print(f"[WARN] Resume ranking logic failed in background: {e}")
        else:
            print(f"[WARN] Skipping ranking logic due to missing data for {email} in job {job_id}")
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        print(f"[ERROR] Exception in background ranking task: {e}")
        db_operations.upsert_candidate(application_data)
        return {"message": "Application submitted successfully"}
    except HTTPException as e:
        # Already a handled error
        raise e
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in apply_for_job: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/candidates/{job_id}")
async def get_candidates_for_job(job_id: str):
    candidates = db_operations.fetch_top_k_candidates_by_count(job_id)
    return {"count": len(candidates), "candidates": candidates}

@app.post("/api/generate-job-description")
def generate_job_description(request: JobDescriptionRequest):
    from services.ai_job_description.generate_description import generate_description
    import json
    import re
    try:
        data = request.dict()
        generated = generate_description(data)
        cleaned = generated.strip()
        # Remove markdown/code block wrappers if present
        if cleaned.lower().startswith('json'):
            cleaned = cleaned.split('\n', 1)[-1]
        cleaned = cleaned.strip('`')
        # Try to parse as JSON directly
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
        # Try to extract first JSON object from the string using regex
        match = re.search(r'({[\s\S]*})', cleaned)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
        # If all parsing fails, raise an error
        raise HTTPException(status_code=500, detail="AI did not return valid JSON. Please try again or check the prompt.")
    except Exception as e:
        import traceback
        print("=== EXCEPTION OCCURRED ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
