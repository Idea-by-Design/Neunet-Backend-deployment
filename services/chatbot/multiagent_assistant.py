import autogen
import os
from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count, fetch_top_k_candidates_by_percentage, update_application_status, execute_sql_query
from services.chatbot.functions import send_email
from ..prompts.multiagent_assistant_prompts import  executor_agent_system_message, fetcher_agent_system_message, email_agent_system_message, job_desc_creator_system_message, sql_query_generator_system_message, initiate_chat_system_message
from dotenv import load_dotenv


# Load environment variables from .env file in the project directory
load_dotenv(dotenv_path=".env")


# Configuration for Azure OpenAI models
config_list = [{"model": os.getenv("deployment_name"),  
                            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                            "base_url": os.getenv("AZURE_OPENAI_ENDPOINT"),
                            "api_type": os.getenv("api_type"),  
                            "api_version": os.getenv("api_version")}]

# Define the User Proxy Agent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=50,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"use_docker": False}
)

# Define the Executor Agent to run functions
executor_agent = autogen.AssistantAgent(
    name="function_executor_agent",
    system_message=executor_agent_system_message,
    llm_config={
        "config_list": config_list,
        "functions": [
            {
                "name": "fetch_top_k_candidates_by_percentage",
                "description": "Fetches the top percentage of candidates (email and ranking only) for a given job ID. ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "number",
                            "description": "The job ID for which to fetch the application data."
                        },
                        "percentage": {
                            "type": "number",
                            "description": "The percentage of top candidates to fetch, defaults to 10%."
                        }
                    },
                    "required": ["job_id"]
                }
            },
            {
                "name": "fetch_top_k_candidates_by_count",
                "description": "Fetches the top count of candidates (email and ranking only) for a given job ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "number",
                            "description": "The job ID for which to fetch the application data."
                        },
                        "percentage": {
                            "type": "number",
                            "description": "The count of top candidates to fetch, defaults to 10."
                        }
                    },
                    "required": ["job_id"]
                }
            },
            {
                "name": "send_email",
                "description": "Sends an email to a list of recipients.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_addresses": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of email addresses to send the email to."
                        },
                        "subject": {
                            "type": "string",
                            "description": "The subject of the email."
                        },
                        "body_plain": {
                            "type": "string",
                            "description": "The plain text content of the email."
                        }
                    },
                    "required": ["to_addresses", "subject", "body_plain"]
                }
            },
            {
                "name": "update_application_status",
                "description": "Updates the status of application for given job application and candidate email id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "number",
                            "description": "The job ID for which to update the application status."
                        },
                        "candidate_email": {
                            "type": "string",
                            "description": "The email of the candidate whose status is to be updated."
                        },
                        "new_status": {
                            "type": "string",
                            "description": "The new status to be set for the candidate."
                        }
                    },
                    "required": ["job_id", "candidate_email", "new_status"]
                }
            },
            {
                "name": "execute_sql_query",
                "description": "Executes the given SQL query generated by the sql_query_generator_agent. This function can be used if there is no other function that solved user request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute."
                        }
                    }
                }
            }

        ]
    },
)

# Register the functions with the executor agent
executor_agent.register_function(
    function_map={
        "fetch_top_k_candidates_by_percentage": fetch_top_k_candidates_by_percentage,
        "fetch_top_k_candidates_by_count": fetch_top_k_candidates_by_count,
        "send_email": send_email,
        "update_application_status": update_application_status,
        "execute_sql_query": execute_sql_query
    }
)

# Define the Fetcher Agent
fetcher_agent = autogen.AssistantAgent(
    name="top_candidate_fetcher",
    system_message=fetcher_agent_system_message,
    llm_config={
        "config_list": config_list,
    },
)


# Define Email Service Agent
email_agent = autogen.AssistantAgent(
    name="email_service_agent",
    system_message=email_agent_system_message,
    llm_config={
        "config_list": config_list,
    },
)


# Define job description creator agent
job_desc_creator_agent = autogen.AssistantAgent(
    name="job_description_creator_agent",
    system_message=job_desc_creator_system_message,
    llm_config={
        "config_list": config_list,
    },
)

# Define SQL Query Generator Agent
sql_query_generator_agent = autogen.AssistantAgent(
    name="sql_query_generator_agent",
    system_message=sql_query_generator_system_message,
    llm_config={
        "config_list": config_list,
    },
)

# Define the Group Chat with the agents
groupchat = autogen.GroupChat(
    agents=[user_proxy, fetcher_agent, job_desc_creator_agent, email_agent, executor_agent, sql_query_generator_agent],
    messages=[],
    max_round=50,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={
    "config_list": config_list,
})

# Initiate the conversation with the User Proxy
def initiate_chat():
    user_proxy.initiate_chat(manager, message=initiate_chat_system_message)



