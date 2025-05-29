import logging
import azure.functions as func
from common.database.cosmos.db_operations import fetch_candidates_with_github_links, store_github_analysis
from services.github_analysis.analyze_github import analyze_github_profile

def main(documents: func.DocumentList) -> str:
    logging.info("GitHub analysis trigger function proceesing", documents)
    if documents:
        for document in documents:
            email = document.get('email')
            github_identifier = document.get('links', {}).get('github')

            if not github_identifier:
                logging.info(f"No GitHub identifier found for {email}")
                continue

            logging.info(f"Analyzing GitHub profile for {email}")

            # Perform GitHub profile analysis
            analysis_data = analyze_github_profile(github_identifier, email)
            analysis_data['email'] = email
            analysis_data['id'] = email

            # Store analysis data in Cosmos DB
            try:
                store_github_analysis(analysis_data)
                logging.info(f"Analysis data stored successfully for {email}")
            except Exception as e:
                logging.error(f"Failed to store analysis data for {email}: {e}")
