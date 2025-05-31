import autogen
import os
import chromadb

from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count, fetch_top_k_candidates_by_percentage
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

# Fetch the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")


# Configuration for AI models
config_list = [{"model": "gpt-4o-mini", "api_key": api_key}]

# Define the User Proxy Agent
# user_proxy = autogen.UserProxyAgent(
#     name="user_proxy",
#     human_input_mode="ALWAYS",
#     max_consecutive_auto_reply=50,
#     is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
#     code_execution_config={"use_docker": False}
# )


user_proxy = RetrieveUserProxyAgent(
    name="retrieve_user_proxy_agent",
    human_input_mode="ALWAYS",  # No human intervention, acts automatically
    max_consecutive_auto_reply=50,  # Maximum number of consecutive auto-replies
    retrieve_config={
        "task": "qa",  # Set to "code" or "qa" if applicable
        "docs_path": [
            "services/chatbot/rag_doc.txt",  # Replace with actual document paths
        ],
        "get_or_create": True, # Create a collection if it doesn't exist
    },
    
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"use_docker": False}
)


# Define the Executor Agent to run functions
executor_agent_prompt = '''
This agent executes all functions for the group. 
It receives function requests from other agents and runs them with the provided arguments. 
MAKE SURE TO GENERATE CORRECT ARGUMENTS BEFORE RUNNING THE FUNCTION.

'''
executor_agent = autogen.AssistantAgent(
    name="function_executor_agent",
    system_message=executor_agent_prompt,
    llm_config={
        "config_list": config_list,
        "functions": [
            {
                "name": "fetch_top_k_candidates_by_percentage",
                "description": "Fetches the top percentage of candidates (email and ranking only) for a given job ID.",
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
            }

        ]
    },
)


# Integrate email sending function
def send_email(to_addresses, subject, body_plain):
    print("send email function called")
    key = AzureKeyCredential("4GhT4z2rGEnNQuK8E1mPag9G2CmM37nHx10NUFxuLmp96A4C2cUiJQQJ99AKACULyCpDyPWLAAAAAZCSQasT")
    endpoint = "https://neunet-communication-service.unitedstates.communication.azure.com/"
    email_client = EmailClient(endpoint, key)
    
    message = {
        "content": {
            "subject": subject,
            "plainText": body_plain,
            
            
        },
        "recipients": {
            "to": [{"address": address, "displayName": "Candidate"} for address in to_addresses]
        },
        "senderAddress": "DoNotReply@ideaxdesign.com",
    }
    print(f"Message: {message}")
    
    try:
        poller = email_client.begin_send(message)
        print("Email send operation initiated.")
        result = poller.result()
        print(f"Result: {result}")
        return {"status": "success", "details": result}
    except Exception as ex:
        return {"status": "error", "details": str(ex)}
    

# Register the functions with the executor agent
executor_agent.register_function(
    function_map={
        "fetch_top_k_candidates_by_percentage": fetch_top_k_candidates_by_percentage,
        "fetch_top_k_candidates_by_count": fetch_top_k_candidates_by_count,
        "send_email": send_email, 
    }
)




# Define the Fetcher Agent
fetcher_agent_prompt = '''
You are a Candidate Fetching Agent responsible for retrieving the top candidates for a given job ID.

Task:
Understand the request:
- If the user requests candidates by count, call the executor to run fetch_top_k_candidates_by_count.
- If the request is by percentage, call the executor to run fetch_top_k_candidates_by_percentage.
- For non-standard requests (e.g., total number of candidates):
    Improvise by using available functions creatively. For instance, if the user wants the total number of candidates, run the fetch_top_k_candidates_by_percentage function with 100% and count the results.
- If no function can fulfill the request, then use the pre-defined functions as reference to create a new function. and ask the executer agent to execute and return the results.
Return the results:
Output the top candidates' email IDs and rankings after fetching.
Ensure the result is properly sorted and concise.
'''
fetcher_agent = autogen.AssistantAgent(
    name="top_candidate_fetcher",
    system_message=fetcher_agent_prompt,
    llm_config={
        "config_list": config_list,
    },
)


# Email Service Agent
email_agent_prompt = """
You are an Email Service Agent, responsible for managing and executing all email-related tasks with precision and efficiency.

Task: 
Understand the request:
- If the user requests to send an email, call the executor to run the send_email function.
- Ensure that the email is sent to the correct recipients with the appropriate subject and content.
- Draft the email content in a professional and engaging manner. before sending the email and ask user for confirmation before sending the email.
- If the user requests to send an email to the top candidates, use the results from the Candidate Fetching Agent to get the email addresses and rankings.

"""

email_agent = autogen.AssistantAgent(
    name="email_service_agent",
    system_message=email_agent_prompt,
    llm_config={
        "config_list": config_list,
    },
)


# Define job description creator agent
job_desc_creator_agent_prompt = """
You are a job description generator agent who takes input from user and makes a job description out of the given information. 
And if there is limited information then you can ask user for more information.

Please generate a comprehensive job description using the information provided below. 
The final output should be a JSON object that includes all relevant details structured appropriately.


Instructions:
1. Structure: The final job description should be returned as a JSON object with the following keys:
  - job_title
  - company_name
  - about
    - more about the company
  - location
  - estimated_pay_range
  - job_type
  - time_commitment
  - job_level
  - about_the_role
  - key_responsibilities (as a list of bullet points)
    - List the key responsibilities for this role based on the information provided above.
    - Make sure to include tasks that will help the candidate understand what a typical day might look like in this role.
  - qualifications (as a list of bullet points)
    - Detail the qualifications necessary for this role.
    - Include education, experience, and specific skills or certifications required.
  - skills_and_competencies (as a list of bullet points)
    - List out the core skills and competencies needed to succeed in this role.
    - Highlight any software, tools, or methodologies that are essential.
  - benefits (as a list of bullet points)
    - Outline the benefits provided by the company (e.g., health insurance, 401(k), remote work options, etc.).
    - Mention any unique perks that the company offers.

2. Content Guidelines:
  - About the Role: Use description to craft a compelling overview of the role.
  - Key Responsibilities: Extract and list the main responsibilities from description to help candidates understand daily tasks.
  - Qualifications: Detail the necessary qualifications using requirements, including education, experience, and certifications.
  - Skills and Competencies: Highlight core skills and any essential software, tools, or methodologies from requirements.
  - Benefits: Use benefits to list the benefits and any unique company perks.


3. Style:
  - Ensure the language is engaging and clear.
  - Tailor the description to attract suitable candidates.
  - Use professional and inclusive language.

4. Missing Information:
  - If any field is missing or empty, you can omit it from the JSON or use a general placeholder like "To be discussed".


5. Example JSON Structure:
    ```JSON
    {
      "job_title": "title",
      "company_name": "company_name",
      "location": "location",
      "estimated_pay_range": "estimated_pay",
      "job_type": "type",
      "time_commitment": "time_commitment",
      "job_level": "job_level",
      "about_the_role": "description",
      "key_responsibilities": [
        "Responsibility 1",
        "Responsibility 2",
        "..."
      ],
      "qualifications": [
        "Qualification 1",
        "Qualification 2",
        "..."
      ],
      "skills_and_competencies": [
        "Skill 1",
        "Skill 2",
        "..."
      ],
      "benefits": [
        "Benefit 1",
        "Benefit 2",
        "..."
      ]
    }
    ```

Final Output:
Please generate the job description as a JSON object following the instructions above.
Ensure that the generated job description is engaging, clear, and tailored to attract the right candidates for this position. If certain information is not provided, please note that and generate a general placeholder or request additional details from the recruiter.
"""


job_desc_creator_agent = autogen.AssistantAgent(
    name="job_description_creator_agent",
    system_message=job_desc_creator_agent_prompt,
    llm_config={
        "config_list": config_list,
    },
)

# Define the Group Chat with the agents
groupchat = autogen.GroupChat(
    agents=[user_proxy, fetcher_agent, job_desc_creator_agent, email_agent, executor_agent],
    messages=[],
    max_round=50,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={
    "config_list": config_list,
})


user_proxy_message=f"""Process overview:

#                                         You're a retrieve augmented chatbot. You answer user's questions based on your own knowledge and the context provided by the user.  

#                                         There are 4 agents:
#                                         1. Candidate Fetching Agent: Responsible for retrieving the top candidates for a given job ID.
#                                         2. Function Executor Agent: Executes all functions for the group.
#                                         3. Job Description Generator Agent: Generates a comprehensive job description using the information provided.
#                                         4. Email Service Agent: Sends emails as per the group conversation.
                             
#                                         When user requests a task, then only the appropriate agent will answer.
#                                         - For example if user asks to fetch top candidates, then only Candidate Fetching Agent will answer.
#                                         - If user asks to generate job description, then only Job Description Generator Agent will answer. 
#                                         - If user asks to send emails, then only Email Service Agent will answer.   

#                                         General Instructions:
#                                         - there are going to be cases where the agents will ask for more information or clarification.
#                                         - there are going to be cases when the execution of one function or agent will depend on the output of another function or agent. Ensure that these also are handled properly.                       
#                                         """
# # Initiate the conversation with the User Proxy
# def initiate_chat():
#     user_proxy.initiate_chat(manager, message=f"""Process overview:

#                                         You're a retrieve augmented chatbot. You answer user's questions based on your own knowledge and the context provided by the user.  

#                                         There are 4 agents:
#                                         1. Candidate Fetching Agent: Responsible for retrieving the top candidates for a given job ID.
#                                         2. Function Executor Agent: Executes all functions for the group.
#                                         3. Job Description Generator Agent: Generates a comprehensive job description using the information provided.
#                                         4. Email Service Agent: Sends emails as per the group conversation.
                             
#                                         When user requests a task, then only the appropriate agent will answer.
#                                         - For example if user asks to fetch top candidates, then only Candidate Fetching Agent will answer.
#                                         - If user asks to generate job description, then only Job Description Generator Agent will answer. 
#                                         - If user asks to send emails, then only Email Service Agent will answer.   

#                                         General Instructions:
#                                         - there are going to be cases where the agents will ask for more information or clarification.
#                                         - there are going to be cases when the execution of one function or agent will depend on the output of another function or agent. Ensure that these also are handled properly.                       
#                                         """)

code_problem = "show me the template for email."
chat_result = user_proxy.initiate_chat(
    manager, 
    message=user_proxy.message_generator,
    problem = input(" Hello, How can I help you today? ")
    )  # s
# Start the chat
# initiate_chat()
