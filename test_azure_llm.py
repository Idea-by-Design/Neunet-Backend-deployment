from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

import openai
import os

# New OpenAI v1.x Azure API usage
client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("api_version"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
deployment_name = os.getenv("deployment_name")
print("Deployment name:", deployment_name)

try:
    response = client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("LLM test response:", response)
except Exception as e:
    print("LLM test error:", e)
