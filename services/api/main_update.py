"""
This is a temporary file containing the updated WebSocket handler code.
We'll use this to update the main.py file using sed or another command line tool.
"""

# Updated WebSocket handler code to use the resume parser utility
websocket_handler_code = """
                                    # Extract LinkedIn and GitHub links using our utility function
                                    from services.utils.resume_parser import extract_linkedin_github_from_resume
                                    
                                    linkedin = ""
                                    github = ""
                                    
                                    # Try to get resume data
                                    if "resume_data" in candidate_data and candidate_data["resume_data"]:
                                        resume_data = candidate_data["resume_data"]
                                        linkedin, github = extract_linkedin_github_from_resume(resume_data)
                                        logging.info(f"[WebSocket] Extracted LinkedIn: {bool(linkedin)}, GitHub: {bool(github)} from resume data")
"""
