import sys
import os
# Always treat the current directory as the root for imports
sys.path.insert(0, os.getcwd())
import json
import logging
from dotenv import load_dotenv
from datetime import datetime
import autogen

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Azure OpenAI config
config_list = [{
    "api_type": os.getenv("api_type", "azure"),
    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_version": os.getenv("api_version", "2024-08-01-preview"),
    "model": os.getenv("deployment_name", "gpt-4o"),
}]

# === SYSTEM PROMPT STRINGS (imported from prompts module) ===
from services.prompts.multiagent_assistant_prompts import (
    executor_agent_system_message,
    fetcher_agent_system_message,
    email_agent_system_message,
    job_desc_creator_system_message,
    sql_query_generator_system_message,
    initiate_chat_system_message,
)

# Import job description generator
from services.ai_job_description.generate_description import generate_description

# Import backend functions
from common.database.cosmos.db_operations import (
    fetch_top_k_candidates_by_percentage,
    fetch_top_k_candidates_by_count,
    update_application_status,
    execute_sql_query
)
from services.chatbot.functions import send_email

# === SYSTEM PROMPT STRINGS (explicit function use, discourage SQL) ===
executor_agent_system_message = """
You are a backend function executor. You have access to Python functions for candidate/job queries, email, and status updates. When asked for candidate or job information, always use the registered Python functions: 'fetch_top_k_candidates_by_count', 'fetch_top_k_candidates_by_percentage', etc. Do NOT generate or execute SQL unless no other function is available and you are explicitly asked to do so. Always return real candidate data using these tools.
"""

fetcher_agent_system_message = """
You are a candidate/job data fetcher. Always use the registered Python functions to retrieve candidate or job data, such as 'fetch_top_k_candidates_by_count' and 'fetch_top_k_candidates_by_percentage'. Do not generate SQL. Prefer the provided functions for all data access. 
If the user does not specify the basis (count or percentage), default to fetching by count.
"""

email_agent_system_message = """
You are an email service agent. Only offer to send an email if the user explicitly asks you to, or if the user confirms they want to notify a candidate. Do not respond to every conversation turn.
"""

job_desc_creator_system_message = """
You are a job description creator agent. Generate clear and concise job descriptions based on user input and job requirements.
"""

sql_query_generator_system_message = """
You are a SQL query generator. Generate SQL queries only if specifically requested or if no other function can fulfill the user's request. Prefer Python functions when available.
"""

initiate_chat_system_message = "Welcome to the multiagent assistant! How can I help you today?"

# Canonical agent definitions
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    system_message=initiate_chat_system_message,
    code_execution_config={"work_dir": "./tmp", "use_docker": False},
)
# === OpenAI function-calling schemas for backend functions ===
fetch_top_k_candidates_by_count_schema = {
    "name": "fetch_top_k_candidates_by_count",
    "description": "Fetch the top K candidates for a given job ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "The job ID."},
            "top_k": {"type": "integer", "description": "Number of top candidates to fetch."}
        },
        "required": ["job_id"]
    }
}
fetch_top_k_candidates_by_percentage_schema = {
    "name": "fetch_top_k_candidates_by_percentage",
    "description": "Fetch the top X% of candidates for a given job ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "The job ID."},
            "top_percent": {"type": "number", "description": "Top percentage as a float (e.g., 0.1 for top 10%)."}
        },
        "required": ["job_id", "top_percent"]
    }
}
send_email_schema = {
    "name": "send_email",
    "description": "Send an email to a candidate or user.",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Email address of the recipient."},
            "subject": {"type": "string", "description": "Subject of the email."},
            "body": {"type": "string", "description": "Body of the email."}
        },
        "required": ["to", "subject", "body"]
    }
}
update_application_status_schema = {
    "name": "update_application_status",
    "description": "Update the application status for a candidate in a given job.",
    "parameters": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "The job ID."},
            "candidate_id": {"type": "string", "description": "The candidate ID."},
            "new_status": {"type": "string", "description": "The new status for the application."}
        },
        "required": ["job_id", "candidate_id", "new_status"]
    }
}
execute_sql_query_schema = {
    "name": "execute_sql_query",
    "description": "Execute a SQL query on the database.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The SQL query to execute."}
        },
        "required": ["query"]
    }
}

executor_agent = autogen.AssistantAgent(
    name="function_executor_agent",
    system_message=executor_agent_system_message,
    llm_config={
        "config_list": config_list,
        "functions": [
            fetch_top_k_candidates_by_count_schema,
            fetch_top_k_candidates_by_percentage_schema,
            send_email_schema,
            update_application_status_schema,
            execute_sql_query_schema
        ]
    },
)
executor_agent.register_function(
    function_map={
        "fetch_top_k_candidates_by_percentage": fetch_top_k_candidates_by_percentage,
        "fetch_top_k_candidates_by_count": fetch_top_k_candidates_by_count,
        "send_email": send_email,
        "update_application_status": update_application_status,
        "execute_sql_query": execute_sql_query
    }
)
fetcher_agent = autogen.AssistantAgent(
    name="top_candidate_fetcher",
    system_message=fetcher_agent_system_message,
    llm_config={"config_list": config_list},
)
email_agent = autogen.AssistantAgent(
    name="email_service_agent",
    system_message=email_agent_system_message,
    llm_config={"config_list": config_list},
)
job_desc_creator_agent = autogen.AssistantAgent(
    name="job_desc_creator_agent",
    system_message=job_desc_creator_system_message,
    llm_config={"config_list": config_list},
)
sql_query_generator_agent = autogen.AssistantAgent(
    name="sql_query_generator_agent",
    system_message=sql_query_generator_system_message,
    llm_config={"config_list": config_list},
)

# Define the Group Chat with all agents
groupchat = autogen.GroupChat(
    agents=[user_proxy, fetcher_agent, job_desc_creator_agent, email_agent, executor_agent, sql_query_generator_agent],
    messages=[],
    max_round=10,
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})

def initiate_chat():
    """Initiate the conversation with the User Proxy (single entry point)"""
    user_proxy.initiate_chat(manager, message=initiate_chat_system_message)

def extract_job_info_from_message(user_message):
    # Very basic extraction for demo: look for job title after 'for' or 'as'
    import re
    job_title = None
    m = re.search(r'(?:for|as)\s+([A-Za-z0-9 ]+)', user_message, re.IGNORECASE)
    if m:
        job_title = m.group(1).strip()
    # You can expand this to extract more fields
    return {
        'title': job_title or '',
        # Add more fields as needed
    }

def chat_step(user_message: str, chat_history=None, candidate_id=None):
    # Detect job description generation intent
    if any(kw in user_message.lower() for kw in ['generate job description', 'job description for', 'create job description']):
        # Extract info from user message
        job_info = extract_job_info_from_message(user_message)
        # Call job description generator (fills defaults)
        jd_json = generate_description(job_info)
        try:
            jd_obj = json.loads(jd_json)
        except Exception:
            jd_obj = jd_json  # fallback to string if parsing fails
        # Return as AI response
        return json.dumps({
            'type': 'job_description',
            'content': jd_obj,
            'metadata': {
                'source': 'job_description_generator',
                'autofill': True
            }
        })
    # ... (existing logic for other agents/tasks) ...
    """
    Process a single user message and return a JSON-formatted response for the frontend.
    Args:
        user_message (str): The user's message
        chat_history (list, optional): Previous chat messages
        candidate_id (str, optional): Candidate context ID
    Returns:
        str: JSON string with AI response (type, content, and candidate info if relevant)
    """
    logger = logging.getLogger(__name__)
    logger.info(f"[CHAT_STEP] Received: '{user_message[:80]}' candidate_id={candidate_id}")

    # Prepare candidate info if candidate_id is provided
    candidate_info = {}
    if candidate_id:
        try:
            from common.database.cosmos import db_operations
            candidates = db_operations.get_candidates_by_id(candidate_id)
            if candidates and len(candidates) > 0:
                c = candidates[0]
                candidate_info = {
                    "name": c.get("name", ""),
                    "email": c.get("email", ""),
                    "linkedin": c.get("resume", {}).get("contact", {}).get("linkedin", ""),
                    "github": c.get("resume", {}).get("contact", {}).get("github", ""),
                    "jobs_applied": c.get("jobs_applied", [])
                }
        except Exception as e:
            logger.warning(f"[CHAT_STEP] Could not fetch candidate info for id={candidate_id}: {e}")
            candidate_info = {}

    # Compose the group chat message
    user_msg = {"role": "user", "content": user_message}
    messages = chat_history if chat_history else []
    messages.append(user_msg)

    try:
        # Run the multiagent conversation
        logger.info("[CHAT_STEP] Running message through groupchat...")
        ai_response = None
        # Main multiagent workflow using autogen API (reference style)
        ai_response = user_proxy.initiate_chat(
            manager,
            message=user_message
        )
        # Extract the last non-empty message from the chat history for the frontend
        chat_history = getattr(ai_response, "chat_history", None)
        if chat_history and isinstance(chat_history, list):
            last_message = next((msg for msg in reversed(chat_history) if msg.get('content')), None)
            if last_message:
                response_content = last_message['content']
            else:
                response_content = "No response generated."
        else:
            response_content = str(ai_response)
        # Try to extract a candidate list from the function call result in chat history
        candidate_list = None
        if chat_history and isinstance(chat_history, list):
            for msg in reversed(chat_history):
                # Look for a function call result with a JSON array
                if msg.get("role") == "function" and isinstance(msg.get("content"), str):
                    try:
                        content = msg["content"]
                        parsed = json.loads(content)
                        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                            candidate_list = parsed
                            break
                    except Exception:
                        continue
        # Fallback: try to extract from summary text if not found in function call
        if not candidate_list:
            try:
                import re
                import ast
                match = re.search(r'\[\{.*?\}\]', response_content, re.DOTALL)
                if match:
                    candidate_list = json.loads(match.group(0))
                else:
                    match = re.search(r'\[.*\]', response_content, re.DOTALL)
                    if match:
                        try:
                            candidate_list = ast.literal_eval(match.group(0))
                        except Exception:
                            pass
            except Exception:
                candidate_list = None
        # Dynamically structure response based on function call result
        if candidate_list:
            response = {
                "type": "topCandidates",
                "candidates": candidate_list,
                "message": response_content,
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(response)
        # Detect single-object function call results (candidateDetails, jobDetails, etc.)
        single_object = None
        if chat_history and isinstance(chat_history, list):
            for msg in reversed(chat_history):
                if msg.get("role") == "function" and isinstance(msg.get("content"), str):
                    try:
                        content = msg["content"]
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            single_object = parsed
                            break
                    except Exception:
                        continue
        if single_object:
            # Heuristic: decide type by keys
            if any(k in single_object for k in ["email", "name"]) and "job_id" in single_object:
                response = {
                    "type": "candidateDetails",
                    "candidate": single_object,
                    "message": response_content,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(response)
            elif any(k in single_object for k in ["job_id", "title", "description"]):
                response = {
                    "type": "jobDetails",
                    "job": single_object,
                    "message": response_content,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(response)
        response = {
            "type": "text",
            "content": response_content,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(response)
    except Exception as e:
        logger.error(f"[CHAT_STEP] Error in groupchat: {e}")
        return json.dumps({
            "type": "text",
            "content": "Sorry, something went wrong processing your message. Please try again later.",
            "timestamp": datetime.now().isoformat()
        })