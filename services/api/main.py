print("=== LOADING main.py ===")
from fastapi import FastAPI, HTTPException, File, UploadFile, Depends, Form, BackgroundTasks, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import random
import os
import sys
import tempfile
import json
import uuid
import time
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.database.cosmos import db_operations
from azure.storage.blob import BlobServiceClient
import io

app = FastAPI(title="Neunet Recruitment API")

# --- CORS Middleware (must be before endpoints) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- Health Check Endpoint ---
@app.get("/health")
async def health_check():
    """Health check endpoint for frontend to verify backend availability"""
    return {"status": "ok", "timestamp": time.time()}

# --- GitHub Analysis Endpoint ---
from services.github_analysis.analyze_github import analyze_github_profile
from fastapi import Body
from pydantic import BaseModel

class GitHubAnalysisRequest(BaseModel):
    github_identifier: str
    candidate_email: str

import uuid

# Import send_email function from chatbot
from services.chatbot.functions import send_email


# --- Helper functions for async GitHub analysis ---
# Deprecated: No longer used. GitHub analysis is now stored per candidate and GitHub identifier.
def save_github_analysis_result(*args, **kwargs):
    pass  # No-op for backward compatibility if called elsewhere.

def fetch_github_analysis_result(candidate_email, github_identifier):
    return db_operations.fetch_github_analysis_by_candidate(candidate_email, github_identifier)

@app.post("/api/github-analysis")
async def github_analysis(request: GitHubAnalysisRequest = Body(...), background_tasks: BackgroundTasks = None):
    import dateutil.parser
    from datetime import datetime, timedelta
    existing_full = db_operations.fetch_github_analysis_by_candidate(request.candidate_email, request.github_identifier, return_full_item=True)
    if existing_full is not None:
        created_at = existing_full.get("created_at")
        is_fresh = False
        if created_at:
            try:
                created_dt = dateutil.parser.isoparse(created_at)
                now = datetime.now(created_dt.tzinfo) if created_dt.tzinfo else datetime.utcnow()
                is_fresh = (now - created_dt) < timedelta(days=183)
            except Exception as e:
                print(f"[WARN] Could not parse created_at for github analysis: {e}")
        if is_fresh:
            return {"success": True, "data": existing_full["result"], "cached": True, "age_days": (now - created_dt).days}
    def run_analysis_and_save():
        try:
            result = analyze_github_profile(request.github_identifier, request.candidate_email)
            db_operations.upsert_github_analysis(request.candidate_email, request.github_identifier, result)
        except Exception as e:
            return {"success": False, "error": str(e)}
    if background_tasks is not None:
        background_tasks.add_task(run_analysis_and_save)
        return {"success": False, "status": "processing"}
    else:
        run_analysis_and_save()
        # Return latest result after sync
        latest_full = db_operations.fetch_github_analysis_by_candidate(request.candidate_email, request.github_identifier, return_full_item=True)
        if latest_full:
            return {"success": True, "data": latest_full["result"], "cached": False}
        else:
            return {"success": False, "error": "Analysis failed or not found."}

@app.get("/api/github-analysis/result/{candidate_email}/{github_identifier}")
async def github_analysis_result(candidate_email: str, github_identifier: str):
    result = db_operations.fetch_github_analysis_by_candidate(candidate_email, github_identifier)
    if result is None:
        return {"status": "processing"}
    return {"success": True, "data": result}

# ------------------- Resume Parser Endpoint -------------------
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

# --- Job Endpoints ---
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

@app.get("/jobs/")
async def list_jobs():
    try:
        jobs = db_operations.fetch_all_jobs()
        return jobs if jobs else []
    except Exception as e:
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

# --- Candidate Endpoints ---
@app.get("/jobs/{job_id}/candidates")
async def get_job_candidates(job_id: str, top_k: int = 10):
    try:
        candidates = db_operations.fetch_top_k_candidates_by_count(job_id, top_k)
        if not candidates:
            return []
        rankings_map = { (job_id, k.strip().lower()): v for k, v in db_operations.fetch_candidate_rankings(job_id).items() }
        patched_candidates = []
        for cand in candidates:
            if not isinstance(cand, dict):
                import sys
                print(f"[SKIP NON-DICT CANDIDATE]: {cand}", file=sys.stderr)
                continue
            resume = cand.get('parsed_resume') or cand.get('resume')
            cand = dict(cand)
            cand['resume'] = resume
            # Ensure 'status' is always present
            if 'status' not in cand or not cand['status']:
                if 'application_status' in cand and cand['application_status']:
                    cand['status'] = cand['application_status']
                else:
                    cand['status'] = 'applied'
            email = (cand.get('email') or '').strip().lower()
            from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
            import re
            # If ranking is missing or zero, re-run ranking synchronously
            ranking_val = 0
            explanation = None
            if email and (job_id, email) in rankings_map:
                raw_ranking = rankings_map[(job_id, email)].get('ranking', 0)
                explanation = rankings_map[(job_id, email)].get('explanation', None)
                if isinstance(raw_ranking, (float, int)) and 0 < raw_ranking <= 1:
                    ranking_val = round(raw_ranking * 100)
                else:
                    ranking_val = round(raw_ranking)
            if ranking_val == 0:
                # Try to re-rank synchronously
                job_description = db_operations.fetch_job_description(job_id)
                job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
                job_questionnaire_id = job_questionnaire_doc['id'] if job_questionnaire_doc else None
                questionnaire = job_questionnaire_doc['questionnaire'] if job_questionnaire_doc else None
                job_description_text = job_description['description'] if job_description and 'description' in job_description else ''
                resume_text = ''
                parsed_resume = cand.get('parsed_resume')
                if parsed_resume and isinstance(parsed_resume, dict) and 'raw_text' in parsed_resume:
                    resume_text = parsed_resume['raw_text']
                if all([job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire]):
                    try:
                        ranking_result = initiate_chat(job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire)
                        if isinstance(ranking_result, dict) and 'score' in ranking_result:
                            ranking_val = ranking_result['score']
                        elif isinstance(ranking_result, (int, float)):
                            ranking_val = ranking_result
                        elif isinstance(ranking_result, str):
                            match = re.search(r"([0-9]+\.?[0-9]*)", ranking_result)
                            if match:
                                ranking_val = float(match.group(1))
                        cand['ranking'] = ranking_val
                        db_operations.upsert_candidate(cand)
                    except Exception as e:
                        print(f"[ERROR] Failed to rerank candidate {email}: {e}")
            else:
                cand['ranking'] = ranking_val
            cand['explanation'] = explanation
            # Patch social links for frontend rendering
            links = None
            if 'parsed_resume' in cand and isinstance(cand['parsed_resume'], dict):
                links = cand['parsed_resume'].get('links', {})
            if links:
                cand['linkedin'] = links.get('linkedIn') or links.get('linkedin') or links.get('LinkedIn')
                cand['github'] = links.get('gitHub') or links.get('github') or links.get('GitHub')
            else:
                cand['linkedin'] = None
                cand['github'] = None
            # Remove CosmosDB metadata fields if present
            for meta_key in ['_rid', '_self', '_etag', '_attachments', '_ts']:
                cand.pop(meta_key, None)
            patched_candidates.append(cand)
        from fastapi.encoders import jsonable_encoder
        try:
            return jsonable_encoder(patched_candidates)
        except Exception as ser_err:
            import json
            import sys
            print("[SERIALIZATION ERROR]", file=sys.stderr)
            print("Patched candidates:", patched_candidates, file=sys.stderr)
            print("Serialization error:", ser_err, file=sys.stderr)
            try:
                json.dumps(patched_candidates)
            except Exception as json_err:
                print("json.dumps error:", json_err, file=sys.stderr)
            raise HTTPException(status_code=500, detail=f"Serialization error: {ser_err}")
    except Exception as e:
        import sys
        print("[CANDIDATE ENDPOINT ERROR]", e, file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates/{candidate_id}")
async def get_candidate_by_id(candidate_id: str):
    try:
        applications_by_id = db_operations.fetch_applications_by_candidate(candidate_id) or []
        applications_by_email = db_operations.fetch_applications_by_candidate_email(candidate_id) or []
        seen = set()
        all_applications = []
        for app in applications_by_id + applications_by_email:
            key = (app.get('job_id'), app.get('email'))
            if key not in seen:
                seen.add(key)
                all_applications.append(app)
        if not all_applications:
            raise HTTPException(status_code=404, detail="Candidate not found")
        profile_fields = [
            'name', 'email', 'avatar', 'role', 'evaluation', 'github', 'skills', 'resume', 'resume_blob_name', 'cover_letter', 'ranking'
        ]
        candidate_profile = {k: all_applications[0].get(k) for k in profile_fields if k in all_applications[0]}
        jobs_applied = []
        for app in all_applications:
            job_id = app.get('job_id')
            job_title = app.get('job_title')
            email = app.get('email')
            if not job_title and job_id:
                job_desc = db_operations.fetch_job_description(job_id)
                job_title = job_desc['title'] if job_desc and 'title' in job_desc else job_id
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
        candidate_profile['ranking'] = max([j['ranking'] for j in jobs_applied] or [0.0])
        parsed_resume = None
        if 'parsed_resume' in all_applications[0] and isinstance(all_applications[0]['parsed_resume'], dict):
            parsed_resume = all_applications[0]['parsed_resume']
            candidate_profile['parsed_resume'] = parsed_resume
        elif 'resume' in all_applications[0] and isinstance(all_applications[0]['resume'], dict):
            parsed_resume = all_applications[0]['resume']
            candidate_profile['parsed_resume'] = parsed_resume
        if parsed_resume and parsed_resume.get('skills'):
            candidate_profile['skills'] = parsed_resume['skills']
        candidate_profile['candidate_id'] = all_applications[0].get('candidate_id') or all_applications[0].get('email')

        # --- Use parsed_resume if present, else parse resume JSON ---
        import json
        parsed_resume = candidate_profile.get('parsed_resume')
        if not parsed_resume:
            resume_str = candidate_profile.get('resume')
            if resume_str:
                try:
                    parsed_resume = json.loads(resume_str)
                except Exception as e:
                    print(f"[ERROR] Failed to parse resume JSON for {candidate_profile.get('email')}: {e}")

        # --- GitHub Analysis Section ---
        import re
        def extract_github_username(github_url_or_username):
            if not github_url_or_username:
                return None
            match = re.search(r"github\.com/([A-Za-z0-9_.-]+)", github_url_or_username)
            if match:
                return match.group(1)
            return github_url_or_username.strip()

        github_username = None
        if parsed_resume:
            links = parsed_resume.get('links', {})
            github_username = (
                links.get('gitHub') or links.get('github') or links.get('GitHub') or
                parsed_resume.get('github') or parsed_resume.get('GitHub')
            )
        # Fallback: check jobsApplied
        if not github_username and candidate_profile.get('jobsApplied'):
            for job in candidate_profile['jobsApplied']:
                if job.get('github'):
                    github_username = job['github']
                    break

        # Extra debug logging for diagnosis
        print(f"[DEBUG] Candidate profile: {candidate_profile}")
        print(f"[DEBUG] Parsed resume: {parsed_resume}")
        norm_github_username = extract_github_username(github_username) if github_username else None
        print(f"[DEBUG] Looking up github_analysis for email={candidate_profile.get('email')}, github_username={norm_github_username}")
        github_analysis = None
        if norm_github_username:
            github_analysis = db_operations.fetch_github_analysis_by_candidate(candidate_profile.get('email'), norm_github_username)
        candidate_profile['github_analysis'] = github_analysis
        return candidate_profile
    except Exception as e:
        print(f"[ERROR] Exception in candidate detail endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Body

@app.post("/jobs/{job_id}/candidates/{candidate_id}/status")
async def update_candidate_status(job_id: str, candidate_id: str, data: dict = Body(...)):
    try:
        status = data.get("status")
        db_operations.update_candidate_status_by_id(job_id, candidate_id, status)
        return {"message": "Status updated successfully"}
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))

# --- Application Endpoints ---
@app.get("/applications/{job_id}")
async def get_job_applications(job_id: str):
    try:
        applications = db_operations.fetch_application_by_job_id(job_id)
        if not applications:
            return []
        return applications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/apply")
async def apply_for_job(
    job_id: str,
    name: str = Form(...),
    email: str = Form(...),
    cover_letter: str = Form(None),
    ranking: float = Form(0.0),
    resume: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    try:
        if resume is None:
            raise HTTPException(status_code=400, detail="No resume file provided.")
        if not hasattr(resume, 'filename') or resume.filename is None:
            raise HTTPException(status_code=400, detail="Resume filename is missing.")
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
            raise HTTPException(status_code=400, detail="Resume file is empty.")
        try:
            blob_client.upload_blob(data, overwrite=True)
            resume_blob_name = blob_name
        except Exception as upload_exc:
            resume_blob_name = None
        parsed_resume = None
        if not resume_blob_name:
            raise HTTPException(status_code=500, detail="Resume upload failed. Please try again.")
        try:
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
            print(f"[DEBUG] Uploaded file: {resume.filename}, suffix: {suffix}")
            print(f"[DEBUG] Parsed resume_text length: {len(text) if text else 0}")
            if not text or not str(text).strip():
                print(f"[ERROR] Resume parsing failed or resume is empty for file: {resume.filename}")
                raise HTTPException(status_code=400, detail="Resume could not be parsed. Please upload a valid PDF or DOCX file with readable text.")
            try:
                parsed_resume = parse_resume_json(text, hyperlinks)
            except Exception as e:
                print(f"[ERROR] Failed to parse resume JSON: {e}")
                parsed_resume = None
        finally:
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
        from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
        job_description = db_operations.fetch_job_description(job_id)
        job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
        job_questionnaire_id = job_questionnaire_doc['id'] if job_questionnaire_doc else None
        questionnaire = job_questionnaire_doc['questionnaire'] if job_questionnaire_doc else None
        resume_text = text if 'text' in locals() else ''
        job_description_text = job_description['description'] if job_description and 'description' in job_description else ''
        ranking_score = ranking
        explanation = None
        print("[DEBUG] Ranking eligibility check:")
        print(f"  job_id: {job_id} (type: {type(job_id)})")
        print(f"  job_questionnaire_id: {job_questionnaire_id} (type: {type(job_questionnaire_id)})")
        print(f"  resume_text: {repr(resume_text)[:100]} (type: {type(resume_text)})")
        print(f"  job_description_text: {repr(job_description_text)[:100]} (type: {type(job_description_text)})")
        print(f"  email: {email} (type: {type(email)})")
        print(f"  questionnaire: {repr(questionnaire)[:100]} (type: {type(questionnaire)})")
        if all([job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire]):
            try:
                ranking_result = initiate_chat(job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire)
                print(f"[DEBUG] Full ranking_result: {repr(ranking_result)}")
                if isinstance(ranking_result, dict):
                    ranking_score = ranking_result.get('score')
                    explanation = ranking_result.get('explanation')
                elif isinstance(ranking_result, (int, float)):
                    ranking_score = ranking_result
                    explanation = None
                elif isinstance(ranking_result, str):
                    import re
                    match = re.search(r"([0-9]+\.?[0-9]*)", ranking_result)
                    if match:
                        ranking_score = float(match.group(1))
                    explanation = None
                if ranking_score is None or explanation is None or not str(explanation).strip():
                    print(f"[ERROR] Ranking or explanation missing. ranking_score: {ranking_score}, explanation: {explanation}, ranking_result: {repr(ranking_result)}")
                    raise HTTPException(status_code=500, detail=f"Ranking or explanation missing from ranking engine. Both are required. Debug: ranking_result={repr(ranking_result)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ranking failed: {e}")
        else:
            raise HTTPException(status_code=500, detail="Insufficient data to perform ranking.")
        application_data = {
            "id": f"{job_id}_{email}",
            "job_id": job_id,
            "name": name,
            "email": email,
            "cover_letter": cover_letter,
            "ranking": ranking_score,
            "explanation": explanation,
            "status": "applied",
            "applied_at": datetime.utcnow().isoformat(),
            "resume_blob_name": resume_blob_name,
            "parsed_resume": parsed_resume,
            "type": "candidate",
        }
        from common.database.cosmos.db_operations import upsert_candidate
        upsert_candidate(application_data)
        # Synchronous ranking: do not use background task
        # rank_candidate_resume_task(job_id, email, resume_blob_name, parsed_resume)  # No longer needed; ranking is immediate
        return {"message": "Application submitted successfully. Ranking is available immediately.", "ranking": ranking_score}
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in apply_for_job: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

def rank_candidate_resume_task(job_id, email, resume_blob_name, parsed_resume):
    try:
        from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
        job_description = db_operations.fetch_job_description(job_id)
        job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
        job_questionnaire_id = job_questionnaire_doc['id'] if job_questionnaire_doc else None
        questionnaire = job_questionnaire_doc['questionnaire'] if job_questionnaire_doc else None
        resume_text = ''
        if parsed_resume and isinstance(parsed_resume, dict) and 'raw_text' in parsed_resume:
            resume_text = parsed_resume['raw_text']
        else:
            try:
                AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                CONTAINER_NAME = "resumes"
                blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
                container_client = blob_service_client.get_container_client(CONTAINER_NAME)
                blob_client = container_client.get_blob_client(resume_blob_name)
                stream = blob_client.download_blob().readall()
                suffix = os.path.splitext(resume_blob_name)[-1].lower()
                fd, temp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                with open(temp_path, "wb") as out_file:
                    out_file.write(stream)
                if suffix == '.pdf':
                    text, hyperlinks = parse_pdf(temp_path)
                elif suffix in ['.doc', '.docx']:
                    text, hyperlinks = parse_doc(temp_path)
                else:
                    text, hyperlinks = '', []
                resume_text = text
                os.remove(temp_path)
            except Exception as e:
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
                    candidate = db_operations.fetch_resume_with_email_and_job(job_id, email)
                    if candidate:
                        candidate['ranking'] = ranking_score
                        db_operations.upsert_candidate(candidate)
            except Exception as e:
                pass
        else:
            pass
    except Exception as e:
        pass

# --- Debug/Admin Endpoint ---
@app.get("/debug/candidates/{job_id}")
async def get_candidates_for_job(job_id: str):
    candidates = db_operations.fetch_top_k_candidates_by_count(job_id)
    return {"count": len(candidates), "candidates": candidates}

# --- AI Job Description Endpoint ---
class JobDescriptionRequest(BaseModel):
    title: str = None
    company_name: str = None
    location: str = None
    type: str = None
    time_commitment: str = None
    description: str = None
    requirements: str = None
    job_id: str = None

@app.post("/api/generate-job-description")
def generate_job_description(request: JobDescriptionRequest):
    from services.ai_job_description.generate_description import generate_description
    import json
    import re
    try:
        data = request.dict()
        generated = generate_description(data)
        cleaned = generated.strip()
        if cleaned.lower().startswith('json'):
            cleaned = cleaned.split('\n', 1)[-1]
        cleaned = cleaned.strip('`')
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
        match = re.search(r'({[\s\S]*})', cleaned)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="AI did not return valid JSON. Please try again or check the prompt.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Email Sending Endpoint ---
from pydantic import BaseModel
from fastapi import APIRouter

class SendEmailRequest(BaseModel):
    to: list[str]
    subject: str
    body: str

@app.post("/api/send-email")
async def api_send_email(request: SendEmailRequest):
    try:
        # Call the backend email sender
        result = send_email(request.to, request.subject, request.body)
        if result.get("status") == "success":
            return {"success": True, "details": result.get("details")}
        else:
            return {"success": False, "error": result.get("details")}
    except Exception as e:
        return {"success": False, "error": str(e)}

from fastapi import WebSocket, WebSocketDisconnect
import threading
import queue
import time
import asyncio

# In-memory chat session store for WebSocket chat
chat_sessions = {}
agent_threads = {}
response_queues = {}

# Function to clean up inactive chat sessions after a timeout
async def cleanup_session_after_timeout(session_id, timeout_seconds):
    """Clean up a chat session after a specified timeout if it's still inactive"""
    await asyncio.sleep(timeout_seconds)
    
    if session_id in chat_sessions:
        # Check if the session is still inactive
        last_active = chat_sessions[session_id].get("last_active", 0)
        time_since_active = time.time() - last_active
        
        if time_since_active >= timeout_seconds:
            try:
                # Put the message in the queue for the agent thread to process
                if session_id in chat_sessions and "input_queue" in chat_sessions[session_id]:
                    chat_sessions[session_id]["input_queue"].put(data)
                    logging.info(f"[WebSocket] Added message to queue for processing")
                    
                    # Send an acknowledgment to the client that the message was received
                    try:
                        ack_message = json.dumps({"type": "ack", "timestamp": time.time(), "message": "Message received and being processed"})
                        await websocket.send_text(ack_message)
                        logging.info(f"[WebSocket] Sent acknowledgment to client")
                    except Exception as ack_error:
                        logging.error(f"[WebSocket] Error sending acknowledgment: {str(ack_error)}")
                else:
                    logging.error(f"[WebSocket] No input queue found for session {session_id}")
                
                # Remove the session
                del chat_sessions[session_id]
                logging.info(f"[WebSocket] Cleaned up inactive session: session_id={session_id}, inactive for {time_since_active:.2f} seconds")
            except Exception as cleanup_error:
                logging.error(f"[WebSocket] Error cleaning up session {session_id}: {str(cleanup_error)}")
        else:
            logging.info(f"[WebSocket] Session {session_id} still active, skipping cleanup")
    else:
        logging.info(f"[WebSocket] Session {session_id} no longer exists, no cleanup needed")

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    # Extract candidate ID from query parameters if present
    candidate_id = None
    try:
        # Get query parameters
        query_params = websocket.query_params
        if query_params and "candidateId" in query_params:
            candidate_id = query_params.get("candidateId")
            logging.info(f"[WebSocket] Extracted candidateId from query params: {candidate_id}")
    except Exception as query_err:
        logging.error(f"[WebSocket] Error extracting query parameters: {str(query_err)}")
    logging.info(f"[WebSocket] New connection attempt: session_id={session_id}")
    
    # Log request headers for debugging
    try:
        headers = websocket.headers
        logging.info(f"[WebSocket] Connection headers: {headers}")
    except Exception as header_err:
        logging.error(f"[WebSocket] Error accessing headers: {str(header_err)}")
    
    # Create input queue if it doesn't exist yet
    if session_id not in chat_sessions:
        logging.info(f"[WebSocket] Creating new session: session_id={session_id}")
        chat_sessions[session_id] = {
            "input_queue": queue.Queue(),
            "history": [],
            "initialized": False,
            "last_active": time.time(),
            "connection_state": "CONNECTED",
            "websocket": websocket,
            "pending_messages": [],  # Initialize pending messages list
            "candidate_id": candidate_id  # Store candidate ID in session
        }
        logging.info(f"[WebSocket] Stored candidateId in session: {candidate_id}")
    elif candidate_id and ("candidate_id" not in chat_sessions[session_id] or chat_sessions[session_id]["candidate_id"] != candidate_id):
        # Update candidate ID if it's changed
        chat_sessions[session_id]["candidate_id"] = candidate_id
        logging.info(f"[WebSocket] Updated candidateId in session: {candidate_id}")
    
    # Get or create input queue for this session
    if "input_queue" not in chat_sessions[session_id]:
        chat_sessions[session_id]["input_queue"] = queue.Queue()
    
    input_queue = chat_sessions[session_id]["input_queue"]
    
    try:
        # Accept the WebSocket connection with explicit CORS handling
        await websocket.accept()
        logging.info(f"[WebSocket] Connection accepted: session_id={session_id}")
        
        # Log connection details
        client = websocket.client
        logging.info(f"[WebSocket] Client connected: {client}")
        
        # Send initial connection confirmation
        try:
            import json  # Import json explicitly in this scope
            confirmation_message = json.dumps({"type": "text", "content": "Connected to chat server successfully."})
            await websocket.send_text(confirmation_message)
            logging.info(f"[WebSocket] Sent connection confirmation message to client: {confirmation_message}")
            
            # Send a ping to verify connection is working
            ping_message = json.dumps({"type": "ping", "timestamp": time.time()})
            await websocket.send_text(ping_message)
            logging.info(f"[WebSocket] Sent ping message to verify connection")
            
            # Check if there are any pending messages to send from previous connection
            if session_id in chat_sessions and "pending_messages" in chat_sessions[session_id] and chat_sessions[session_id]["pending_messages"]:
                pending_messages = chat_sessions[session_id]["pending_messages"]
                logging.info(f"[WebSocket] Found {len(pending_messages)} pending messages to deliver")
                
                for pending_msg in pending_messages:
                    try:
                        await websocket.send_text(pending_msg)
                        logging.info(f"[WebSocket] Delivered pending message: {pending_msg[:50]}...")
                    except Exception as pending_error:
                        logging.error(f"[WebSocket] Error sending pending message: {str(pending_error)}")
                
                # Clear pending messages after sending
                chat_sessions[session_id]["pending_messages"] = []
        except Exception as confirm_error:
            logging.error(f"[WebSocket] Error sending confirmation message: {str(confirm_error)}")
            # Try a plain text message as fallback
            try:
                await websocket.send_text('{"type": "text", "content": "Connected to chat server."}') 
                logging.info(f"[WebSocket] Sent fallback plain text connection confirmation")
            except Exception as fallback_error:
                logging.error(f"[WebSocket] Error sending fallback confirmation: {str(fallback_error)}")
        
        # Update last active time for the session
        chat_sessions[session_id]["last_active"] = time.time()
    
        # Agent thread function removed - now processing messages directly in main loop

        # WebSocket timeout is handled by FastAPI automatically
        logging.info(f"[WebSocket] WebSocket connection established with default timeout")
            
        # Start a background task for ping/pong
        ping_task = None
        
        from starlette.websockets import WebSocketState

        async def ping_pong():
            """Send periodic pings to keep the connection alive"""
            try:
                while True:
                    await asyncio.sleep(30)  # Send ping every 30 seconds
                    if websocket.client_state == WebSocketState.CONNECTED:
                        try:
                            ping_message = {"type": "ping", "timestamp": time.time()}
                            await websocket.send_text(json.dumps(ping_message))
                            logging.debug(f"[WebSocket] Sent ping message")
                        except Exception as ping_error:
                            logging.error(f"[WebSocket] Error sending ping: {str(ping_error)}")
                            break
                    else:
                        logging.warning(f"[WebSocket] Connection not active, stopping ping")
                        break
            except Exception as e:
                logging.error(f"[WebSocket] Error in ping_pong: {str(e)}")
        
        # Start the ping task
        ping_task = asyncio.create_task(ping_pong())
        
        try:
            while True:
                # Wait for messages from the client
                message = await websocket.receive_text()
                logging.info(f"[WebSocket] Received user message from frontend: {message[:100]}...")
                
                try:
                    # Parse the incoming message
                    data = json.loads(message)
                    
                    # Handle ping/pong messages
                    if data.get("type") == "ping":
                        pong_message = {"type": "pong", "timestamp": time.time()}
                        await websocket.send_text(json.dumps(pong_message))
                        continue
                    elif data.get("type") == "pong":
                        logging.debug(f"[WebSocket] Received pong from client")
                        continue
                    
                    # Accept both {text: ...} and {type: 'text', content: ...} message formats
                    user_message = (
                        data.get("content") or
                        data.get("text") or
                        ""
                    )
                    user_message = user_message.strip()

                    # Accept context from either format
                    context = data.get("context", {})
                    candidate_id = context.get("candidateId") or data.get("candidateId")

                    if not user_message:
                        logging.warning(f"[WebSocket] Received empty message")
                        continue
                    
                    # Send processing acknowledgment immediately
                    processing_message = {
                        "type": "text",
                        "content": f"I received your message: '{user_message}'. Processing your request...",
                        "isProcessing": True
                    }
                    await websocket.send_text(json.dumps(processing_message))
                    logging.info(f"[WebSocket] Sent processing acknowledgment")
                    
                    # Process the message with multiagent assistant
                    try:
                        from services.chatbot.multiagent_assistant import chat_step
                        
                        # Call chat_step with optional candidate_id
                        ai_response_json = chat_step(
                            user_message=user_message,
                            chat_history=None,
                            candidate_id=candidate_id
                        )
                        
                        # Parse the JSON response from chat_step
                        try:
                            ai_response_data = json.loads(ai_response_json)
                            
                            # Add timestamp and metadata to the response
                            ai_response_data["timestamp"] = time.time()
                            ai_response_data["isProcessing"] = False
                            
                            # Add or update metadata
                            if "metadata" not in ai_response_data:
                                ai_response_data["metadata"] = {}
                            ai_response_data["metadata"].update({
                                "using_fallback": False,
                                "using_real_ai_response": True,
                                "response_source": "multiagent_assistant"
                            })
                            
                            # Send the final response directly
                            await websocket.send_text(json.dumps(ai_response_data))
                            
                        except json.JSONDecodeError as parse_error:
                            logging.error(f"[WebSocket] Failed to parse AI response JSON: {str(parse_error)}")
                            # Fallback: treat as plain text
                            fallback_response = {
                                "type": "text",
                                "content": ai_response_json,
                                "isProcessing": False,
                                "timestamp": time.time(),
                                "metadata": {
                                    "using_fallback": True,
                                    "using_real_ai_response": True,
                                    "response_source": "multiagent_assistant",
                                    "parse_error": str(parse_error)
                                }
                            }
                            await websocket.send_text(json.dumps(fallback_response))
                        logging.info(f"[WebSocket] Sent final AI response")
                        
                    except Exception as ai_error:
                        logging.error(f"[WebSocket] Error in AI processing: {str(ai_error)}")
                        
                        # Send error response
                        error_response = {
                            "type": "text",
                            "content": "I'm sorry, I encountered an error processing your request. Please try again.",
                            "isProcessing": False,
                            "timestamp": time.time(),
                            "metadata": {
                                "error": True,
                                "error_message": str(ai_error)
                            }
                        }
                        await websocket.send_text(json.dumps(error_response))
                        
                except json.JSONDecodeError:
                    logging.error(f"[WebSocket] Invalid JSON received: {message}")
                except Exception as msg_error:
                    logging.error(f"[WebSocket] Error processing message: {str(msg_error)}")
                    
        except WebSocketDisconnect as disconnect_error:
            logging.info(f"[WebSocket] WebSocket disconnected during message loop: {str(disconnect_error)}")
        except Exception as loop_error:
            logging.error(f"[WebSocket] Error in message loop: {str(loop_error)}")
                    
    except WebSocketDisconnect:
        logging.info(f"[WebSocket] Client disconnected from session {session_id}")
    except Exception as e:
        logging.error(f"[WebSocket] WebSocket error: {str(e)}")
    finally:
        # Clean up
        if ping_task:
            ping_task.cancel()
        if session_id in chat_sessions:
            chat_sessions[session_id]["last_active"] = time.time()
        logging.info(f"[WebSocket] WebSocket connection closed for session {session_id}")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
