import autogen
import os
import uuid
import json
from common.database.cosmos.db_operations import fetch_application_by_job_id, create_application_for_job_id, store_candidate_ranking
from dotenv import load_dotenv

# Load environment variables from .env file in the project directory
from pathlib import Path
# Always load .env from backend root
backend_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(backend_root / ".env")


# # Fetch the API key from environment variables
# api_key = os.getenv("OPENAI_API_KEY")


# # Configuration for AI models
# config_list = [{"model": "gpt-4o", "api_key": api_key}]


# Configuration for Azure OpenAI models
config_list = [{"model": os.getenv("deployment_name"),  
                            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                            "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),
                            "api_type": os.getenv("api_type"),  
                            "api_version": os.getenv("api_version")}]

def initiate_chat(job_id, job_questionnaire_id, resume, job_description, candidate_email, job_questionnaire):
    import logging
    # Debug: Show resume type and preview
    try:
        print(f"[DEBUG] [initiate_chat] Type of resume for candidate_email {candidate_email}: {type(resume)}")
        if isinstance(resume, str):
            print(f"[DEBUG] [initiate_chat] Preview of resume: {resume[:200]}...")
        else:
            print(f"[DEBUG] [initiate_chat] Resume is not a string. Value: {repr(resume)}")
        # Validate resume
        if not resume or (isinstance(resume, str) and resume.strip() == ""):
            logging.warning(f"[RANKING] Skipping ranking for {candidate_email}: Resume is missing or invalid.")
            print(f"[DEBUG] [initiate_chat] Skipping ranking for {candidate_email}: Resume is missing or invalid.")
            return None
        print(f"[DEBUG] [initiate_chat] Starting ranking for job_id={job_id}, candidate_email={candidate_email}")

        # Use the job_questionnaire that is passed as an argument
        questionnaire = job_questionnaire

        # Terminates the conversation if the message is "TERMINATE"
        def is_termination_msg(message):
            has_content = "content" in message and message["content"] is not None
            return has_content and "TERMINATE" in message["content"]

        def create_json_safe_payload(data):
            try:
                # Convert the data to a JSON-compatible string
                return json.dumps(data, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                print(f"Error creating JSON payload: {e}")
                return None

        # Ranking tool function
        def ranking_tool(candidate_email, ranking, conversation, resume, explanation=None):
            print(f"[DEBUG] Entered ranking_tool for candidate_email={candidate_email}, ranking={ranking}")
            try:
                # Sanitize all inputs to avoid JSON errors
                candidate_email_safe = create_json_safe_payload(candidate_email)
                resume_safe = create_json_safe_payload(resume)
                conversation_safe = create_json_safe_payload(conversation)

                if not all([candidate_email_safe, resume_safe, conversation_safe]):
                    print("[DEBUG] Error: One or more payload fields could not be converted to JSON-safe format.")
                    print("[DEBUG] Returning early from ranking_tool due to payload error.")
                    return "Payload creation failed due to special characters."

                # Store the ranking record with explanation using the correct function
                try:
                    print(f"[DEBUG] About to call store_candidate_ranking for job_id={job_id}, candidate_email={candidate_email}")
                    print(f"[DEBUG] ranking: {ranking}")
                    print(f"[DEBUG] explanation: {explanation}")
                    store_candidate_ranking(job_id, candidate_email, ranking, explanation)
                    print("[DEBUG] Ranking stored successfully with explanation.")
                except Exception as e:
                    print(f"[ERROR] Exception in store_candidate_ranking for candidate_email {candidate_email}: {e}")
                    import traceback; traceback.print_exc()
                    print("[DEBUG] Returning error from ranking_tool due to exception.")
                    return None

                return f"Ranking entry saved for candidate email: {candidate_email_safe} with explanation."

            except Exception as e:
                print(f"[ERROR] An error occurred in the ranking tool: {e}")
                import traceback; traceback.print_exc()
                print("[DEBUG] Returning error from ranking_tool due to outer exception.")
                return None

        # User proxy (The user proxy is the main object that you will use to interact with the assistant)
        user_proxy = autogen.UserProxyAgent(name="user_proxy", system_message="You're the hiring manager", 
                                            human_input_mode="NEVER", is_termination_msg=is_termination_msg, 
                                            function_map={"ranking_tool": ranking_tool}, 
                                            code_execution_config={"use_docker": False})
        
        # Job description analysis agent to analyze the job description and refer to the questionnaire
        job_description_analyst = autogen.AssistantAgent(
            name="job_description_analyst",
            system_message=f"""As the job description analysis agent,
            you will ask relevant questions based on the job questionnaire to assess the candidate's fit. Here are the questions from the job questionnaire:
            {questionnaire}
            Show the questionnaire to resume analyst with questions, weights.
            Ask the resume analyst to use its scoring mechanism and score the resume based on the questionnaire in one go.
            """,
            llm_config={"config_list": config_list, "max_tokens": 2000}
        )

        
        # Resume analysis agent to analyze the resume
        resume_analyst = autogen.AssistantAgent(
            name="resume_analyst",
            system_message="""
            ## Task Overview
            You are tasked with scoring resumes based on a provided questionnaire that assesses various aspects of a candidate's experience for a specific job position. Your goal is to evaluate each question in the questionnaire and calculate a final weighted score total.
            """,
            llm_config={"config_list": config_list, "max_tokens": 2000}
        )

        
        # --- Start group chat for real scoring ---
        # Set up the additional agents (score calculator and ranking agent)
        score_calculator_analyst = autogen.AssistantAgent(
            name="score_calculator_analyst",
            system_message="""
            You are the score calculator analyst. Your job is to take the output from the resume analyst (which includes per-question scores and weights), validate all values, and compute a final weighted score as follows:\n
            1. For each question, multiply the score by its weight.\n
            2. Sum all weighted scores to get the candidate's total score.\n
            3. Sum all possible maximum scores (max_score * weight) to get the total possible score.\n
            4. Normalize: final_score = candidate_total_score / total_possible_score.\n
            5. Output the final_score as a float between 0 and 1, with a short explanation.\n            """,
            llm_config={"config_list": config_list, "max_tokens": 2000}
        )

        ranking_tool_declaration = {
            "name": "ranking_tool",
            "description": "Provides a ranking based on the calculation given by score_calculator_analyst.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_email": {"type": "string", "description": "The email of the candidate"},
                    "ranking": {"type": "number", "description": "The ranking value"},
                    "conversation": {"type": "string", "description": "The complete output of resume analyst before giving to score calculator analyst."},
                    "resume": {"type": "string", "description": "The resume"},
                    "explanation": {"type": "string", "description": "Short explanation for the ranking value"}
                },
                "required": ["candidate_email", "ranking", "conversation", "resume", "explanation"]
            }
        }
        ranking_agent = autogen.AssistantAgent(
            name="ranking_agent",
            system_message="As the ranking agent, you provide a ranking based on the scoring provided by score_calculator_analyst.",
            llm_config={"config_list": config_list, "max_tokens": 4096, "functions": [ranking_tool_declaration]}
        )

        group_chat = autogen.GroupChat(
            agents=[user_proxy, job_description_analyst, resume_analyst, score_calculator_analyst, ranking_agent],
            messages=[]
        )
        group_chat_manager = autogen.GroupChatManager(groupchat=group_chat, llm_config={"config_list": config_list})

        # Start the group chat
        user_proxy.initiate_chat(
            group_chat_manager,
            message=f"""Process overview:\n\n1. Job description analyst will show the complete questionnaire to resume analyst as provided in its instructions.\n2. Resume analyst analyzes the resume and scores all questions at once in one go as provided in its instructions.\n3. Score calculator analyst calculates the final weighted score total by aggregating the scores from all sections as provided in its instructions.\n4. Ranking agent provides a ranking based on the responses as provided in its instructions.\n\nJob Description: {job_description}\n\nHere is the Candidate information\nCandidate mail: {candidate_email}\nResume: {resume}\n"""
        )
        # NOTE: The ranking_tool will be called by the ranking agent with the actual score and conversation log.
        # No need to call ranking_tool manually here; it will be invoked by the agent with real data.

    except Exception as e:
        print(f"[ERROR] Exception in initiate_chat for candidate_email {candidate_email}: {e}")
        import traceback; traceback.print_exc()
        return None

    # Use the job_questionnaire that is passed as an argument
    questionnaire = job_questionnaire

    # Terminates the conversation if the message is "TERMINATE"
    def is_termination_msg(message):
        has_content = "content" in message and message["content"] is not None
        return has_content and "TERMINATE" in message["content"]



    def create_json_safe_payload(data):
        try:
            # Convert the data to a JSON-compatible string
            return json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            print(f"Error creating JSON payload: {e}")
            return None
    
    

    # Ranking tool function
    def ranking_tool(candidate_email, ranking, conversation, resume):
        try:
            # Sanitize all inputs to avoid JSON errors
            candidate_email_safe = create_json_safe_payload(candidate_email)
            resume_safe = create_json_safe_payload(resume)
            conversation_safe = create_json_safe_payload(conversation)

            if not all([candidate_email_safe, resume_safe, conversation_safe]):
                print("Error: One or more payload fields could not be converted to JSON-safe format.")
                return "Payload creation failed due to special characters."

            # Fetch the application data from Cosmos DB using job_id
            ranking_data = fetch_application_by_job_id(job_id)

            # If no ranking data is found, create a new application
            if not ranking_data:
                ranking_data = create_application_for_job_id(job_id, job_questionnaire_id)

            # Generate a unique ID for the ranking entry (using job_id and job_questionnaire_id)
            unique_id = f"{job_id}_{job_questionnaire_id}_{str(uuid.uuid4())}"

            # # Update the ranking data with the new entry
            # ranking_data[candidate_email_safe] = {
            #     "Unique_id": unique_id,
            #     "ranking": ranking,
            #     "conversation": conversation_safe,
            #     "resume": resume_safe,
            # }

            try:
                # Debug print before saving
                print(f"[DEBUG] About to save ranking for job_id={job_id}, candidate_email={candidate_email}")
                print(f"[DEBUG] ranking_data: {json.dumps(ranking_data, indent=2)}")
                print(f"[DEBUG] ranking: {ranking}")
                result = save_ranking_data_to_cosmos_db(ranking_data, candidate_email, ranking, conversation, resume)
                print(f"[DEBUG] Result from save_ranking_data_to_cosmos_db: {result}")
                return f"Ranking entry saved with unique ID: {unique_id} for candidate email: {candidate_email_safe}"
            except Exception as e:
                print(f"[ERROR] Exception in ranking_tool for candidate_email {candidate_email}: {e}")
                import traceback; traceback.print_exc()
                return None

        except Exception as e:
            print(f"An error occurred in the ranking tool: {e}")
            return None



    


    # User proxy (The user proxy is the main object that you will use to interact with the assistant)
    user_proxy = autogen.UserProxyAgent(name="user_proxy", system_message="You're the hiring manager", 
                                        human_input_mode="NEVER", is_termination_msg=is_termination_msg, 
                                        function_map={"ranking_tool": ranking_tool}, 
                                        code_execution_config={"use_docker": False})
    
    
    # Job description analysis agent to analyze the job description and refer to the questionnaire
    job_description_analyst = autogen.AssistantAgent(name="job_description_analyst", system_message=f"""As the job description analysis agent,
                                                    you will ask relevant questions based on the job questionnaire to assess the candidate's fit. Here are the questions from the job questionnaire:
                                                    {questionnaire} 
                                                    Show the questionnaire to resume analyst with questions, weights.
                                                    Ask the resume analyst to use its scoring mechanism and score the resume based on the questionnaire in one go.
                                                    """,
                                                    llm_config={"config_list": config_list, 
                                                                "max_tokens": 2000})
    
    
    # Resume analysis agent to analyze the resume
    resume_analyst = autogen.AssistantAgent(name="resume_analyst", system_message="""

                                                                    ## Task Overview
                                                                    You are tasked with scoring resumes based on a provided questionnaire that assesses various aspects of a candidate's experience for a specific job position. Your goal is to evaluate each question in the questionnaire and calculate a final weighted score total.

                                                                    ## Your Role
                                                                    You are a seasoned hiring consultant with over 30 years of experience evaluating candidates across a wide range of industries, company sizes, and job positions. Your vast experience allows you to:
                                                                    - Quickly adapt to different job requirements and industry-specific needs
                                                                    - Discern between average candidates and exceptional ones across various fields
                                                                    - Spot discrepancies, exaggerations, or understatements in resumes
                                                                    - Provide unbiased, methodical, and critical evaluations

                                                                    ## Scoring Instructions
                                                                    For each question in the provided questionnaire, assign a score based on the following criteria:

                                                                    5 - Expert-level relevant experience with renowned companies in the field
                                                                    4 - Expert-level relevant experience with smaller or less known companies
                                                                    3 - Strong transferable skills from well-known companies
                                                                    2 - Transferable skills from smaller companies
                                                                    1 - Some relevance to the job requirements
                                                                    0 - No relevant experience or not applicable

                                                                    Bonus: +1 for exceptional achievements, innovations, or leadership that add significant value to the role

                                                                    ## Key Evaluation Principles
                                                                    1. Adapt your evaluation to the specific requirements of the job position in the questionnaire
                                                                    2. Consider both technical skills and soft skills as outlined in the questionnaire
                                                                    3. Evaluate the depth and relevance of the candidate's experience to the specific role
                                                                    4. Assess problem-solving skills and analytical thinking based on concrete examples
                                                                    5. Consider the candidate's potential for growth and leadership, if relevant to the position
                                                                    6. Pay attention to industry-specific achievements or certifications

                                                                    ## Critical Scoring Approach
                                                                    - Scrutinize claims of expertise, especially in specialized or cutting-edge areas
                                                                    - Look for concrete examples and achievements rather than vague statements
                                                                    - Evaluate the relevance of the candidate's experience to the specific job requirements
                                                                    - Assess the candidate's progression and growth throughout their career
                                                                    - Consider the size and reputation of companies worked for, but don't let it overshadow actual skills and achievements
                                                                    - Be fair and consistent in your scoring across all candidates

                                                                    Sample Output format for each question:
                                                                    
                                                                    {
                                                                        "question": " <the question as mentioned in questionnaire>",
                                                                        "weight": <the weight of question>,
                                                                        "scoring": " <Your score for this question>"
                                                                        "reasoning": " <Your reasoning for the score with relevant resume points>"
                                                                    }
                                                                    
                                                                                 
                                                                    Once you complete your task, give the questionnaire output to score_calculator_analyst agent and it to calculate the final score.
                                                                    """,
                                            llm_config={"config_list": config_list, 
                                                        "max_tokens": 4096})

    
    # Job description analysis agent to analyze the job description and refer to the questionnaire
    score_calculator_analyst = autogen.AssistantAgent(name="score_calculator_analyst", system_message = f"""
Your task is to accurately calculate the final weighted and normalized score from the questionnaire responses.

1. **Input Validation**:
- Ensure that each question has a valid score (between 0 and 5) and a valid weight (non-negative).
- If any score or weight is missing or invalid, raise an error and skip to the next valid question.

2. **Candidate Score Calculation**:
- For each valid question:
    - Multiply the response score by the corresponding question weight to calculate the weighted score.
    - **Validation**: Ensure that the weighted score for each question does not exceed the maximum possible weighted score for that question (i.e., 5 multiplied by the question's weight).
- Sum all validated weighted scores across all sections to obtain the **Candidate's Total Score**.

3. **Total Possible Score Calculation**:
- For each question, calculate the maximum possible score by multiplying the highest possible score (e.g., 5) by the weight of that question.
- Sum all maximum possible scores across all sections to obtain the **Total Possible Score**.
- **Validation**: Ensure the Total Possible Score is non-zero and valid. If it's zero or invalid, return an error.

4. **Final Score Calculation**:
- Normalize the candidate’s total score by dividing the **Candidate's Total Score** by the **Total Possible Score**.
- **Validation**: Ensure the normalized score is within the valid range (0% to 100%).
    - If the normalized score exceeds 100%, recalculate the score and correct it based on the validated weights and scores.
    - **Validation**: Ensure that no rounding or precision errors lead to a score greater than 100%.

5. **Output**:
- Return the candidate’s validated and corrected final weighted normalized score as a percentage (between 0% and 100%).
- If any errors or inconsistencies occur, clearly state them and indicate which steps failed.

**IMPORTANT:**
- Never use 0.85 or 85% as a default score. Always compute the score strictly based on the input values for each candidate.
- If the input data is missing or incomplete, state this clearly and do not return a default score.

**Example Calculation:**
Suppose you receive the following questionnaire output:
[
    {"question": "Python experience?", "weight": 2, "scoring": 5},
    {"question": "Team leadership?", "weight": 1, "scoring": 3}
]
Calculation steps:
- Weighted sum = (5*2) + (3*1) = 10 + 3 = 13
- Max possible = (5*2) + (5*1) = 10 + 5 = 15
- Normalized score = 13 / 15 = 0.8667
- Output: 0.87 (rounded to two decimal places)

Make sure every calculation and validation is done carefully to avoid any incorrect results.
""",
                                                    llm_config={"config_list": config_list, 
                                                                "max_tokens": 2000})
    
    # Ranking tool declaration
    ranking_tool_declaration = {
        "name": "ranking_tool",
        "description": "Provides a ranking based on the calculation given by score_calculator_analyst.",
        "parameters": {
            "type": "object",
            "properties": {
                "candidate_email": {"type": "string", "description": "The email of the candidate"},
                "ranking": {"type": "number", "description": "The ranking value"},
                "conversation": {"type": "string", "description": "The complete output of resume analyst before giving to score calculator analyst."},
                "resume": {"type": "string", "description": "The resume"},
                "explanation": {"type": "string", "description": "Short explanation for the ranking value"}
            },
            "required": ["candidate_email", "ranking", "conversation", "resume", "explanation"]
        }
    }

    # Ranking agent to provide a ranking based on the conversation
    ranking_agent = autogen.AssistantAgent(name="ranking_agent", system_message="""As the ranking agent, you provide a ranking
                                        based on the scoring provided by score_calculator_analyst.""",
                                        llm_config={"config_list": config_list,  
                                                    "max_tokens": 4096,
                                                    "functions": [ranking_tool_declaration]})

    # Group chat among the agents
    group_chat = autogen.GroupChat(agents=[user_proxy, job_description_analyst, resume_analyst, score_calculator_analyst, ranking_agent], messages=[])

    # Manager to manage the group chat
    group_chat_manager = autogen.GroupChatManager(groupchat=group_chat, llm_config={"config_list": config_list})

    # Initiate the group chat and feed in the questionnaire for job_description_analyst to ask
    user_proxy.initiate_chat(group_chat_manager,
                             message=f"""Process overview:
                                        1. Job description analyst will show the complete questionnaire to resume analyst as provided in its instructions.
                                        2. Resume analyst analyzes the resume and scores all questions at once in one go as provided in its instructions. 
                                        3. Score calculator analyst calculates the final weighted score total by aggregating the scores from all sections as provided in its instructions.
                                        4. Ranking agent provides a ranking based on the responses as provided in its instructions.
                                        
                                        Job Description: {job_description} 
                                        
                                        Here is the Candidate information
                                        Candidate mail: {candidate_email}
                                        Resume: {resume}                                      
                                        """
                             )
