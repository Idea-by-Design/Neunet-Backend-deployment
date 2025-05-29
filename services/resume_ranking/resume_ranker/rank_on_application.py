import sys
import os
import json
from services.resume_ranking.resume_ranker.multiagent_resume_ranker import initiate_chat
from common.database.cosmos.db_operations import (
    fetch_job_description,
    fetch_job_description_questionnaire,
    fetch_resume_with_email
)

def rank_candidate_on_application(job_id, candidate_email):
    """
    Call this function as soon as a candidate applies for a job.
    It fetches all required data and triggers the ranking logic.
    """
    print(f"[INFO] Ranking candidate {candidate_email} for job {job_id}")
    # Fetch job description
    job_description = fetch_job_description(job_id)
    # Fetch job questionnaire
    job_questionnaire = fetch_job_description_questionnaire(job_id)
    questionnaire_id = job_questionnaire['id']
    questions = job_questionnaire['questionnaire']
    # Fetch candidate resume
    resume = fetch_resume_with_email(candidate_email)
    # Run ranking logic
    result = initiate_chat(
        job_id,
        questionnaire_id,
        resume,
        job_description,
        candidate_email,
        questions
    )
    print(f"[INFO] Ranking result for {candidate_email}: {result}")
    return result

if __name__ == "__main__":
    # Example usage for manual testing
    job_id = input("Enter job_id: ").strip()
    candidate_email = input("Enter candidate_email: ").strip()
    rank_candidate_on_application(job_id, candidate_email)
