import os
import logging
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_azure_openai_connection():
    """Test direct connection to Azure OpenAI API"""
    try:
        # Get configuration from environment variables
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("api_version")
        deployment_name = os.getenv("deployment_name")
        
        # Log configuration (without exposing the API key)
        logger.info(f"Testing Azure OpenAI connection with:")
        logger.info(f"API Base: {api_base}")
        logger.info(f"API Version: {api_version}")
        logger.info(f"Deployment Name: {deployment_name}")
        logger.info(f"API Type: azure")
        
        # Configure the client
        client = openai.AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=api_base
        )
        
        # Make a simple completion request
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello world"}
            ],
            max_tokens=50
        )
        
        # Log and return the response
        logger.info(f"Response received: {response}")
        logger.info(f"Generated text: {response.choices[0].message.content}")
        return True, response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error connecting to Azure OpenAI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, str(e)

if __name__ == "__main__":
    success, message = test_azure_openai_connection()
    print(f"Test {'succeeded' if success else 'failed'}: {message}")
