import os
import sys
from dotenv import load_dotenv
import openai
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_azure_openai_connection():
    """Test connection to Azure OpenAI API with specific configuration"""
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("api_version")
    deployment_name = os.getenv("deployment_name")
    
    logger.info(f"AZURE_OPENAI_API_KEY present: {bool(api_key)}")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {endpoint}")
    logger.info(f"api_version: {api_version}")
    logger.info(f"deployment_name: {deployment_name}")
    
    # First, test basic HTTP connectivity to the endpoint
    try:
        response = requests.get(endpoint, timeout=5)
        logger.info(f"Basic HTTP connection to endpoint: Status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Basic HTTP connection failed: {str(e)}")
    
    # Now test the actual API with proper configuration
    try:
        # Configure Azure OpenAI client
        client = openai.AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        logger.info("Azure OpenAI client configured successfully")
        
        # Test the API by listing available models
        try:
            models = client.models.list()
            logger.info(f"Successfully listed models: {[model.id for model in models.data]}")
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
        
        # Try a simple completion request
        try:
            logger.info(f"Attempting chat completion with model: {deployment_name}")
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                max_tokens=50
            )
            
            logger.info("Chat completion API request successful!")
            logger.info(f"Response: {response.choices[0].message.content}")
            return True
        except Exception as e:
            logger.error(f"Error with chat completion: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"Error configuring Azure OpenAI client: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    return False

if __name__ == "__main__":
    success = test_azure_openai_connection()
    sys.exit(0 if success else 1)
