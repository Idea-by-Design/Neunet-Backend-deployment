"""
Batch script to re-run ranking for all candidates with ranking=0 for all jobs in the database.
"""
import sys
import os
import time
from dotenv import load_dotenv

# Ensure correct sys.path for absolute imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, '.env'))

from common.database.cosmos import db_operations
from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat


def rerank_candidates_with_zero(job_id):
    candidates = db_operations.fetch_top_k_candidates_by_count(job_id, top_k=1000)
    reranked = 0
    for cand in candidates:
        needs_rerank = cand.get('ranking', 0) == 0 or not cand.get('explanation') or not str(cand.get('explanation')).strip()
        if needs_rerank:
            try:
                job_description = db_operations.fetch_job_description(job_id)
                job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
                if not job_description or not job_questionnaire_doc:
                    print(f"[SKIP] Missing job description or questionnaire for job_id {job_id}")
                    continue
                questionnaire_id = job_questionnaire_doc['id']
                questions = job_questionnaire_doc['questionnaire']
                resume = cand.get('parsed_resume') or cand.get('resume')
                email = cand.get('email')
                if not resume or not email:
                    print(f"[SKIP] Missing resume or email for candidate in job_id {job_id}")
                    continue
                result = initiate_chat(job_id, questionnaire_id, resume, job_description, email, questions)
                import re
                ranking_score = None
                explanation = None
                if isinstance(result, dict):
                    ranking_score = result.get('ranking')
                    explanation = result.get('explanation')
                else:
                    import re
                    match = re.search(r"([0-9]+\.?[0-9]*)", str(result))
                    if match:
                        ranking_score = float(match.group(1))
                    explanation = None
                if explanation and str(explanation).strip():
                    cand['ranking'] = ranking_score
                    cand['explanation'] = explanation
                    db_operations.upsert_candidate(cand)
                    reranked += 1
                    print(f"[RERANKED] {email} for job {job_id}: {ranking_score}\nExplanation: {explanation}")
                else:
                    print(f"[WARN] Explanation missing for {email} in job {job_id}. Candidate NOT updated.")
            except Exception as e:
                print(f"[ERROR] Failed to rerank candidate {cand.get('email')} for job {job_id}: {e}")
    print(f"[INFO] Reranked {reranked} candidates for job {job_id}")

def main():
    jobs = db_operations.fetch_all_jobs()
    print(f"Found {len(jobs)} jobs in the database.")
    for job in jobs:
        job_id = job.get('job_id') or job.get('id')
        if not job_id:
            print(f"[WARN] Job missing job_id: {job}")
            continue
        rerank_candidates_with_zero(job_id)
    print("Batch reranking complete.")

if __name__ == "__main__":
    main()
