import os
from common.database.cosmos import db_operations
from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat

def rerank_candidates_with_zero(job_id):
    candidates = db_operations.fetch_top_k_candidates_by_count(job_id, top_k=1000)
    job_description = db_operations.fetch_job_description(job_id)
    job_questionnaire_doc = db_operations.fetch_job_description_questionnaire(job_id)
    job_questionnaire_id = job_questionnaire_doc['id'] if job_questionnaire_doc else None
    questionnaire = job_questionnaire_doc['questionnaire'] if job_questionnaire_doc else None
    job_description_text = job_description['description'] if job_description and 'description' in job_description else ''
    reranked = []
    for cand in candidates:
        email = cand.get('email')
        if not email:
            continue
        ranking = cand.get('ranking', 0)
        if ranking == 0:
            resume_text = ''
            parsed_resume = cand.get('parsed_resume')
            if parsed_resume and isinstance(parsed_resume, dict) and 'raw_text' in parsed_resume:
                resume_text = parsed_resume['raw_text']
            # Optionally, fetch from blob if needed
            if all([job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire]):
                try:
                    ranking_result = initiate_chat(job_id, job_questionnaire_id, resume_text, job_description_text, email, questionnaire)
                    if isinstance(ranking_result, dict) and 'score' in ranking_result:
                        ranking_score = ranking_result['score']
                    elif isinstance(ranking_result, (int, float)):
                        ranking_score = ranking_result
                    elif isinstance(ranking_result, str):
                        import re
                        match = re.search(r"([0-9]+\.?[0-9]*)", ranking_result)
                        if match:
                            ranking_score = float(match.group(1))
                        else:
                            ranking_score = 0
                    else:
                        ranking_score = 0
                    cand['ranking'] = ranking_score
                    db_operations.upsert_candidate(cand)
                    reranked.append((email, ranking_score))
                except Exception as e:
                    print(f"[ERROR] Failed to rerank candidate {email}: {e}")
    print(f"Reranked candidates: {reranked}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python rerank_zero_candidates.py <job_id>")
        exit(1)
    job_id = sys.argv[1]
    rerank_candidates_with_zero(job_id)
