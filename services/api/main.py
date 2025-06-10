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
import tempfile

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
)

# --- GitHub Analysis Endpoint ---
from services.github_analysis.analyze_github import analyze_github_profile
from fastapi import Body
from pydantic import BaseModel

class GitHubAnalysisRequest(BaseModel):
    github_identifier: str
    candidate_email: str

import uuid

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
            patched_candidates.append(cand)
        return patched_candidates
    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
